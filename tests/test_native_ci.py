"""离线回归检查：资源不能被 HTML 回退页代替，分发包必须在源码外验证。"""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile
from email.message import Message
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "native_ci", Path(__file__).resolve().parents[1] / ".github/scripts/native_ci.py")
ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ci)


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.body = b"\x89PNG\r\n\x1a\n\xff\x00"
        (self.root / "logo.png").write_bytes(self.body)
        self.env = {"PROJECT_DIR": ".", "HTTP_RESOURCES_JSON": json.dumps([
            {"path": "/logo.png", "source": "logo.png", "content_type": "image/png"}])}
        self.root_patch = patch.object(ci, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.env_patch = patch.dict(os.environ, self.env)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def opener(self, body, content_type="image/png", status=200):
        response = io.BytesIO(body)
        response.headers = Message()
        response.headers["Content-Type"] = content_type
        response.status = status
        return Mock(open=Mock(return_value=response))

    def test_png_compared_as_bytes(self):
        opener = self.opener(self.body)
        ci.check_resources(opener, "http://127.0.0.1:8080/health")
        opener.open.assert_called_once_with("http://127.0.0.1:8080/logo.png", timeout=5)

    def test_spa_html_fallback_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "MIME"):
            ci.check_resources(self.opener(b"<html>fallback</html>", "text/html"), "http://127.0.0.1/health")

    def test_right_type_wrong_bytes_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "内容不一致"):
            ci.check_resources(self.opener(b"not the expected png"), "http://127.0.0.1/health")

    def test_non_success_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "状态"):
            ci.check_resources(self.opener(self.body, status=404), "http://127.0.0.1/health")

    def test_external_resource_urls_are_rejected(self):
        for url in ("https://example.com/image", "//example.com/image", "///example.com/image", "/image\n"):
            with self.subTest(url=url), patch.dict(os.environ, HTTP_RESOURCES_JSON=json.dumps([
                {"path": url, "source": "logo.png", "content_type": "image/png"}])):
                with self.assertRaises(ValueError):
                    ci.resource_cases()

    def test_external_source_is_rejected(self):
        with patch.dict(os.environ, HTTP_RESOURCES_JSON=json.dumps([
            {"path": "/logo.png", "source": "../private.png", "content_type": "image/png"}])):
            with self.assertRaises(ValueError):
                ci.resource_cases()

    def test_redirect_is_not_followed(self):
        self.assertIsNone(ci.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com"))


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "dist").mkdir()
        self.env_patch = patch.dict(os.environ, PROJECT_DIR=".", ARTIFACT_NAME="app",
                                    NATIVE_TARGET="macos-arm64", BINARY_PATH="target/app{exe}")
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.root_patch = patch.object(ci, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def archive(self, member_name="app-macos-arm64/app"):
        archive = ci.archive_path()
        with tarfile.open(archive, "w:gz") as bundle:
            # 此处只测试分发包边界；真实二进制及服务由离线原生集成验证覆盖。
            member = tarfile.TarInfo(member_name)
            member.size = 7
            member.mode = 0o755
            bundle.addfile(member, io.BytesIO(b"fixture"))
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_name(archive.name + ".sha256").write_text(f"{checksum}  {archive.name}\n")
        return archive

    def test_run_from_extracted_bundle_outside_source(self):
        self.archive()
        visited = []
        def inspect(output, cwd):
            self.assertFalse(cwd.is_relative_to(self.root))
            self.assertEqual(output.parent, cwd)
            self.assertEqual(output.read_bytes(), b"fixture")
            visited.append(cwd)
        with patch.object(ci, "verify_binary", side_effect=inspect):
            ci.verify()
        self.assertEqual(len(visited), 1)
        self.assertFalse(visited[0].exists(), "验证临时目录应清理")

    def test_corrupt_archive_is_rejected_before_execution(self):
        self.archive().write_bytes(b"corrupted")
        with patch.object(ci, "verify_binary") as run:
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                ci.verify()
            run.assert_not_called()

    def test_archive_path_traversal_is_rejected(self):
        self.archive("../escape")
        with patch.object(ci, "verify_binary") as run:
            with self.assertRaisesRegex(ValueError, "路径"):
                ci.verify()
            run.assert_not_called()

    def test_windows_zip_uses_extracted_executable(self):
        with patch.dict(os.environ, NATIVE_TARGET="windows-amd64"):
            archive = ci.archive_path()
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("app-windows-amd64/app.exe", b"windows fixture")
            checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
            archive.with_name(archive.name + ".sha256").write_text(f"{checksum}  {archive.name}\n")
            def inspect(output, cwd):
                self.assertFalse(cwd.is_relative_to(self.root))
                self.assertEqual(output.name, "app.exe")
                self.assertEqual(output.read_bytes(), b"windows fixture")
            with patch.object(ci, "verify_binary", side_effect=inspect) as run:
                ci.verify()
                run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
