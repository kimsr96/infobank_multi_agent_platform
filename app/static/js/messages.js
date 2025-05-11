// messages.js: 메시지 표시, 토글, 필터 관련 함수

function escapeHtmlAndRemoveStrikethrough(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\u0336/g, ""); // Remove Unicode strikethrough
}

export function showMessagesPlaceholder(messagesDiv) {
  if (!messagesDiv.querySelector('.messages-placeholder')) {
    const placeholder = document.createElement('div');
    placeholder.className = 'messages-placeholder';
    placeholder.textContent = '무엇을 도와드릴까요?';
    messagesDiv.appendChild(placeholder);
  }
}

export function removeMessagesPlaceholder(messagesDiv) {
  const ph = messagesDiv.querySelector('.messages-placeholder');
  if (ph) ph.remove();
}

export function displayMessage(data) {
  const { source, content } = data;
  if (!content || !content.text) return;
  const messagesDiv = document.getElementById('messages');
  const messageDiv = document.createElement('div');
  if (source === 'host_request' || source === 'host_agent') {
    messageDiv.className = 'message host-request left-align host-message';
    messageDiv.dataset.source = source;
    let headerText = source === 'host_agent' ? 'Host Agent' : 'Host Request';
    const isAgent = source === 'host_agent';
    const display = isAgent ? 'block' : 'none';
    const icon = isAgent ? '−' : '+';
    messageDiv.innerHTML = `
      <div class="message-header host-message-header">
        <div class="header-content">
          <span>${headerText}</span>
          <button class="message-toggle" onclick="toggleMessage(this)">
            <span class="toggle-icon">${icon}</span>
          </button>
        </div>
      </div>
      <div class="message-content" style="display: ${display};">${escapeHtmlAndRemoveStrikethrough(content.text)}</div>
    `;
  } else if (source === 'task') {
    messageDiv.className = `message agent`;
    messageDiv.dataset.source = source;
    let headerText = content.role || 'Agent';
    messageDiv.innerHTML = `
      <div class="message-header">
        <div class="header-content">
          <span>${headerText}</span>
          <button class="message-toggle" onclick="toggleMessage(this)" title="내용 보기/숨기기">
            <span class="toggle-icon">+</span>
          </button>
        </div>
      </div>
      <div class="message-content" style="display: none;">${escapeHtmlAndRemoveStrikethrough(content.text)}</div>
    `;
  } else {
    messageDiv.className = `message ${source} ${content.role}`;
    messageDiv.dataset.source = source;
    let headerText = source === 'agent' ? 'Host Agent' : source;
    messageDiv.innerHTML = `
      <div class="message-header">
        <div class="header-content">
          <span>${headerText}</span>
        </div>
      </div>
      <div class="message-content">${escapeHtmlAndRemoveStrikethrough(content.text)}</div>
    `;
  }
  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

export function toggleMessage(button) {
  const messageDiv = button.closest('.message');
  const content = messageDiv.querySelector('.message-content');
  const icon = button.querySelector('.toggle-icon');
  if (content.style.display === 'none') {
    content.style.display = 'block';
    icon.textContent = '−';
  } else {
    content.style.display = 'none';
    icon.textContent = '+';
  }
}

export function updateMessageVisibility(messageFilters) {
  document.querySelectorAll('.message').forEach(msg => {
    const source = msg.dataset.source;
    msg.style.display = messageFilters[source] ? 'block' : 'none';
  });
}
