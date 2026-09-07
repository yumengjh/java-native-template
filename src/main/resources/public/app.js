// 仅由用户点击触发本地请求，没有轮询、遥测或外部请求。
const button = document.querySelector('#check');
const status = document.querySelector('#status');
button.addEventListener('click', async () => {
  button.disabled = true;
  try {
    const response = await fetch('/health');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    status.textContent = `${data.status} · ${data.message}`;
  } catch (error) {
    status.textContent = `请求失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
});
