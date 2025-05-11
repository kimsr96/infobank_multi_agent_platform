// agent_modal.js: 에이전트 추가/미리보기/모달 관련 함수 및 이벤트

export function setupAgentModal(renderAgentList) {
  const addAgentModal = document.getElementById('add-agent-modal');
  const addAgentFormModal = document.getElementById('add-agent-form-modal');
  const showAddAgentBtn = document.getElementById('show-add-agent-form');
  const cancelAddAgentModalBtn = document.getElementById('cancel-add-agent-modal');
  const newAgentUrlModalInput = document.getElementById('new-agent-url-modal');
  const previewBtn = document.getElementById('preview-agent-btn');
  const agentCardModal = document.getElementById('agent-card-modal');
  const agentCardPreview = document.getElementById('agent-card-preview');
  const addAgentConfirmBtn = document.getElementById('add-agent-confirm-btn');
  const cancelAgentCardModalBtn = document.getElementById('cancel-agent-card-modal');

  // Add Agent 버튼 클릭 시 모달 열기
  showAddAgentBtn.onclick = function() {
    addAgentModal.style.display = 'flex';
    newAgentUrlModalInput.value = '';
    newAgentUrlModalInput.focus();
  };

  // 취소 버튼 또는 오버레이 클릭 시 모달 닫기
  cancelAddAgentModalBtn.onclick = function() {
    addAgentModal.style.display = 'none';
  };
  addAgentModal.onclick = function(e) {
    if (e.target === addAgentModal) addAgentModal.style.display = 'none';
  };

  // Add Agent 폼 제출 시 새로운 에이전트를 서버에 추가
  addAgentFormModal.onsubmit = async function(e) {
    e.preventDefault();
    const url = newAgentUrlModalInput.value.trim();
    if (!url) return;
    try {
      const res = await fetch('/agents', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url})
      });
      if (!res.ok) throw Error('에이전트 추가 실패');
      const data = await res.json();
      if (data.success) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar.classList.contains('closed')) {
          document.getElementById('sidebar-toggle').click();
        } else {
          await renderAgentList();
        }
      } else if (data.fail === false && data.error) {
        addAgentConfirmBtn.style.display = 'none'; 
        cancelAgentCardModalBtn.style.display = 'inline-block';
      } else {
        addAgentConfirmBtn.style.display = 'none';
        alert('에이전트 추가 실패');
      }
    } catch {
      addAgentConfirmBtn.style.display = 'none';
      alert('에이전트 추가 실패');
    }
    addAgentModal.style.display = 'none';
  };

  // 에이전트 카드 미리보기 버튼 클릭 시 에이전트 정보 표시
  previewBtn.onclick = async function(e) {
    e.preventDefault();
    const url = newAgentUrlModalInput.value.trim();
    if (!url) return;
    agentCardPreview.innerHTML = '<div class="loading">에이전트 정보를 불러오는 중...</div>';
    agentCardModal.style.display = 'flex';
    try {
      const res = await fetch('/agent_card_preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      const data = await res.json();
      if (res.ok && data.success !== false) {
        const content = document.createElement('div');
        content.className = 'agent-card-info';
        const nameDiv = document.createElement('div');
        nameDiv.className = 'info-row';
        nameDiv.innerHTML = `<strong>Name:</strong> ${data.name || 'Unnamed Agent'}`;
        content.appendChild(nameDiv);
        if (data.description) {
          const descDiv = document.createElement('div');
          descDiv.className = 'info-row';
          descDiv.innerHTML = `<strong>Description:</strong> ${data.description}`;
          content.appendChild(descDiv);
        }
        if (data.tools && data.tools.length > 0) {
          const toolsDiv = document.createElement('div');
          toolsDiv.className = 'info-row';
          toolsDiv.innerHTML = '<strong>Tools:</strong>';
          const toolsList = document.createElement('ul');
          data.tools.forEach(tool => {
            const li = document.createElement('li');
            li.textContent = `${tool.name}${tool.description ? ': ' + tool.description : ''}`;
            toolsList.appendChild(li);
          });
          toolsDiv.appendChild(toolsList);
          content.appendChild(toolsDiv);
        }
        if (data.capabilities && data.capabilities.length > 0) {
          const capDiv = document.createElement('div');
          capDiv.className = 'info-row';
          capDiv.innerHTML = '<strong>Capabilities:</strong>';
          const capList = document.createElement('ul');
          data.capabilities.forEach(cap => {
            const li = document.createElement('li');
            li.textContent = cap;
            capList.appendChild(li);
          });
          capDiv.appendChild(capList);
          content.appendChild(capDiv);
        }
        agentCardPreview.innerHTML = '';
        agentCardPreview.appendChild(content);
        addAgentConfirmBtn.style.display = 'inline-block';
        addAgentConfirmBtn.disabled = false;
      } else {
        agentCardPreview.innerHTML = '<div class="error">에이전트 정보를 불러올 수 없습니다.</div>';
        addAgentConfirmBtn.style.display = 'none';
        addAgentConfirmBtn.disabled = true;
      }
    } catch (err) {
      console.error('Agent card preview error:', err);
      agentCardPreview.innerHTML = '<div class="error">에이전트 정보를 불러오는 중 오류가 발생했습니다.</div>';
      addAgentConfirmBtn.style.display = 'none';
      addAgentConfirmBtn.disabled = true;
    }
    cancelAgentCardModalBtn.style.display = 'inline-block';
  };

  // 에이전트 추가 버튼 클릭 시
  addAgentConfirmBtn.onclick = async function(e) {
    e.preventDefault();
    const url = newAgentUrlModalInput.value.trim();
    if (!url) return;
    try {
      const res = await fetch('/agents', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url})
      });
      const data = await res.json();
      if (data.success) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar.classList.contains('closed')) {
          document.getElementById('sidebar-toggle').click();
        } else {
          await renderAgentList();
        }
        agentCardModal.style.display = 'none';
        addAgentModal.style.display = 'none';
      } else {
        agentCardPreview.innerHTML = `<span style="color:#d32f2f">${'에이전트 정보를 불러올 수 없습니다.'}</span>`;
      }
    } catch {
      agentCardPreview.innerHTML = `<span style="color:#d32f2f">${'에이전트 추가 실패'}</span>`;
    }
  };

  // 미리보기 모달에서 "취소" 클릭 시 닫기
  cancelAgentCardModalBtn.onclick = function() {
    agentCardModal.style.display = 'none';
  };
}
