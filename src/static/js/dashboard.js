document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation Tabs ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active-tab'));
            
            btn.classList.add('active');
            const targetId = `tab-${btn.dataset.tab}`;
            document.getElementById(targetId).classList.add('active-tab');
            
            if (btn.dataset.tab === 'curation') loadLogs();
        });
    });

    // --- Tab 1: Curation ---
    const logList = document.getElementById('logList');
    const editorPanel = document.getElementById('editorPanel');
    const editorPrompt = document.getElementById('editorPrompt');
    const editorResponse = document.getElementById('editorResponse');
    const saveBtn = document.getElementById('saveBtn');
    const exportBtn = document.getElementById('exportBtn');
    
    let currentLogs = [];
    let activeLogIndex = -1;

    async function loadLogs() {
        try {
            const res = await fetch('/api/dashboard/logs');
            const data = await res.json();
            currentLogs = data;
            renderLogs();
        } catch (e) {
            console.error("Failed to load logs", e);
        }
    }

    function renderLogs() {
        logList.innerHTML = '';
        currentLogs.slice().reverse().forEach((log, reversedIndex) => {
            const index = currentLogs.length - 1 - reversedIndex;
            const userMsg = log.messages.find(m => m.role === 'user');
            
            const div = document.createElement('div');
            div.className = `log-item ${index === activeLogIndex ? 'active' : ''}`;
            div.innerHTML = `
                <div class="log-meta">
                    <span>${new Date(log.timestamp).toLocaleString()}</span>
                    <span>路由: ${log.metadata.route_used}</span>
                </div>
                <div class="log-prompt">${userMsg ? userMsg.content : '無提問'}</div>
            `;
            
            div.addEventListener('click', () => selectLog(index));
            logList.appendChild(div);
        });
    }

    function selectLog(index) {
        activeLogIndex = index;
        renderLogs();
        
        const log = currentLogs[index];
        const userMsg = log.messages.find(m => m.role === 'user');
        const astMsg = log.messages.find(m => m.role === 'assistant');
        
        editorPrompt.textContent = userMsg ? userMsg.content : '';
        editorResponse.value = astMsg ? astMsg.content : '';
        editorPanel.style.display = 'block';
    }

    saveBtn.addEventListener('click', async () => {
        if (activeLogIndex === -1) return;
        
        const originalLog = currentLogs[activeLogIndex];
        const correctedText = editorResponse.value;
        
        saveBtn.textContent = '儲存中...';
        try {
            const res = await fetch('/api/dashboard/logs/correct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_log: originalLog,
                    corrected_response: correctedText
                })
            });
            
            if (res.ok) {
                saveBtn.textContent = '已儲存！';
                setTimeout(() => saveBtn.textContent = '驗證並儲存', 2000);
            } else {
                alert('校正儲存失敗。');
                saveBtn.textContent = '驗證並儲存';
            }
        } catch (e) {
            console.error(e);
            saveBtn.textContent = '驗證並儲存';
        }
    });

    exportBtn.addEventListener('click', () => {
        window.location.href = '/api/dashboard/export';
    });

    // --- Tab 2: Upload Data ---
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const folderInput = document.getElementById('folderInput');
    const btnSelectFiles = document.getElementById('btnSelectFiles');
    const btnSelectFolder = document.getElementById('btnSelectFolder');
    const uploadStatus = document.getElementById('uploadStatus');

    btnSelectFiles.addEventListener('click', () => fileInput.click());
    btnSelectFolder.addEventListener('click', () => folderInput.click());
    
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', () => handleFiles(fileInput.files));
    folderInput.addEventListener('change', () => handleFiles(folderInput.files));

    async function handleFiles(files) {
        if (!files.length) return;
        
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('file', files[i]);
        }
        
        const dataType = document.getElementById('dataTypeSelect').value;
        formData.append('data_type', dataType);
        
        uploadStatus.innerHTML = `<span style="color:var(--accent-color)">正在處理與上傳 ${files.length} 個檔案...（OCR 轉換可能需要幾十秒）</span>`;
        
        try {
            const res = await fetch('/api/dashboard/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await res.json();
            if (res.ok) {
                uploadStatus.innerHTML = `<span style="color:#4ade80">成功上傳 ${data.files.length} 個檔案！</span>`;
            } else {
                uploadStatus.innerHTML = `<span style="color:#f87171">上傳失敗：${data.error}</span>`;
            }
        } catch (e) {
            uploadStatus.innerHTML = `<span style="color:#f87171">上傳時發生網路錯誤。</span>`;
        }
        
        fileInput.value = '';
    }

    // --- Tab 3: Live Chat ---
    const chatHistory = document.getElementById('chatHistory');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');

    function addMessageToChat(role, text, route = null) {
        const div = document.createElement('div');
        div.className = `message ${role === 'user' ? 'user-msg' : 'bot-msg'}`;
        div.textContent = text;
        if (route) {
            div.innerHTML += `<span class="route-badge">經由 ${route}</span>`;
        }
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;
        
        addMessageToChat('user', text);
        chatInput.value = '';
        chatInput.disabled = true;
        chatSendBtn.disabled = true;
        
        try {
            const res = await fetch('/api/chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: 'dashboard_test_user',
                    message: text
                })
            });
            const data = await res.json();
            addMessageToChat('bot', data.reply, data.route_used);
        } catch (e) {
            addMessageToChat('bot', '與伺服器通訊時發生錯誤。');
        } finally {
            chatInput.disabled = false;
            chatSendBtn.disabled = false;
            chatInput.focus();
        }
    }

    chatSendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Initial Load
    loadLogs();
});
