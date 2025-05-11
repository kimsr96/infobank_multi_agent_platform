// main.js: 엔트리포인트, 각 모듈 초기화 및 연결

import { addWebSocketHandlers, addSubmitHandler } from './websocket.js';
import { showMessagesPlaceholder, removeMessagesPlaceholder, displayMessage, toggleMessage, updateMessageVisibility } from './messages.js';
import { setupSidebarToggle, renderAgentList } from './sidebar.js';
import { setupAgentModal } from './agent_modal.js';

// 최초 실행 시 필요한 요소와 WebSocket 연결
const sessionId = Math.random().toString().substring(10);
const ws_url = "ws://" + window.location.host + "/ws/" + sessionId;
let ws = new WebSocket(ws_url);

const messagesDiv = document.getElementById("messages");
const messageFilters = {
    agent: true,
    task: true,
    system: true
};

showMessagesPlaceholder(messagesDiv);

// 메시지 필터 체크박스 이벤트 등록
if (document.querySelectorAll('.message-controls input').length) {
  document.querySelectorAll('.message-controls input').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
      const source = this.id.replace('show-', '');
      messageFilters[source] = this.checked;
      updateMessageVisibility(messageFilters);
    });
  });
}

// WebSocket 핸들러 등록
addWebSocketHandlers(
  ws,
  ws_url,
  (wsArg) => addSubmitHandler(wsArg, (div=messagesDiv) => removeMessagesPlaceholder(div)),
  displayMessage,
  () => removeMessagesPlaceholder(messagesDiv),
  () => updateMessageVisibility(messageFilters)
);

// 사이드바 토글 및 에이전트 리스트
setupSidebarToggle(renderAgentList);

// 에이전트 추가 및 모달 관련
setupAgentModal(renderAgentList);

// 메시지 토글 함수 전역 등록 (HTML onclick용)
window.toggleMessage = toggleMessage;
