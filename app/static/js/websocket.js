// websocket.js: WebSocket 연결 및 핸들러 관련 함수

export function addWebSocketHandlers(ws, ws_url, addSubmitHandler, displayMessage, removeMessagesPlaceholder, updateMessageVisibility) {
  ws.onopen = function () {
    document.getElementById("sendButton").disabled = false;
    addSubmitHandler(this);
  };

  ws.onmessage = function (event) {
    removeMessagesPlaceholder();
    const packet = JSON.parse(event.data);
    if (packet.type === 'message' && packet.source !== 'user') {
        displayMessage(packet);
    } else if (!packet.type && packet.role !== 'user') {
        const message = document.createElement("p");
        message.className = packet.role || "agent";
        message.innerText = packet.message;
        document.getElementById("messages").appendChild(message);
    }
    document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
  };

  ws.onclose = function () {
    document.getElementById("sendButton").disabled = true;
    setTimeout(function () {
      ws = new WebSocket(ws_url);
      addWebSocketHandlers(ws, ws_url, addSubmitHandler, displayMessage, removeMessagesPlaceholder, updateMessageVisibility);
    }, 5000);
  };

  ws.onerror = function (e) {
    // 오류 처리 (필요시 추가)
  };
}

export function addSubmitHandler(ws, removeMessagesPlaceholder) {
  const messageForm = document.getElementById("messageForm");
  const messageInput = document.getElementById("message");
  const messagesDiv = document.getElementById("messages");
  messageForm.onsubmit = function (e) {
    e.preventDefault();
    removeMessagesPlaceholder();
    const message = messageInput.value;
    if (message) {
      const p = document.createElement("p");
      p.className = "user";
      p.textContent = message;
      messagesDiv.appendChild(p);
      ws.send(message);
      messageInput.value = "";
    }
    return false;
  };
}
