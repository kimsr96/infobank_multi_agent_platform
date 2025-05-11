// sidebar.js: 사이드바 토글 및 에이전트 리스트 관리

export function setupSidebarToggle(renderAgentList) {
  const sidebarToggleBtn = document.getElementById('sidebar-toggle');
  sidebarToggleBtn.onclick = async function() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('closed');
    if (!sidebar.classList.contains('closed')) {
      await renderAgentList();
    }
  };
}

export async function renderAgentList() {
  try {
    const res = await fetch('/agents');
    const data = await res.json();
    const agentList = document.getElementById('agent-list');
    agentList.innerHTML = '';
    data.agents.forEach(agent => {
      const li = document.createElement('li');
      li.textContent = agent.name;
      // 삭제 버튼 추가
      const delBtn = document.createElement('button');
      delBtn.textContent = 'X';
      delBtn.className = 'delete-agent-btn';
      delBtn.onclick = async function(e) {
        e.stopPropagation();
        if (!confirm('이 에이전트를 삭제할까요?')) return;
        try {
          const res = await fetch('/agents', {
            method: 'DELETE',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({url: agent.url})
          });
          const result = await res.json();
          if (result.success) {
            agentList.removeChild(li);
          } else if (result.fail === false && result.error) {
            alert(result.error);
          } else {
            alert('에이전트 삭제 실패');
          }
        } catch {
          alert('에이전트 삭제 실패');
        }
      };
      li.appendChild(delBtn);
      agentList.appendChild(li);
    });
  } catch (e) {
    alert('에이전트 목록을 불러오지 못했습니다.');
  }
}
