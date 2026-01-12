const ws = new WebSocket(`ws://${location.host}/ws/tags`);

ws.onmessage = (evt) => {
  const msg = JSON.parse(evt.data);
  if (msg.type === 'update') {
    document.getElementById(msg.tag).textContent = msg.value;
  }
};
