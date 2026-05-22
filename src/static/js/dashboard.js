document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation Tabs ---
    const tabBtns = document.querySelectorAll('nav.nav-tabs .tab-btn');
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
    let currentDrafts = []; // Store nightly Hermes drafts
    let activeLogIndex = -1;

    async function loadLogs() {
        try {
            // Load both logs and drafts in parallel
            const [logsRes, draftsRes] = await Promise.all([
                fetch('/api/dashboard/logs'),
                fetch('/api/dashboard/drafts')
            ]);
            currentLogs = await logsRes.json();
            currentDrafts = await draftsRes.json();
            renderLogs();
        } catch (e) {
            console.error("Failed to load logs or drafts", e);
        }
    }

    function renderLogs() {
        logList.innerHTML = '';
        currentLogs.slice().reverse().forEach((log, reversedIndex) => {
            const index = currentLogs.length - 1 - reversedIndex;
            const userMsg = log.messages.find(m => m.role === 'user');
            
            // Check if this log has a corresponding Hermes draft
            const userPrompt = userMsg ? userMsg.content : '';
            const hasDraft = currentDrafts.some(d => d.original_interaction.messages[0].content === userPrompt);

            const div = document.createElement('div');
            div.className = `log-item ${index === activeLogIndex ? 'active' : ''} ${hasDraft ? 'has-draft' : ''}`;
            div.innerHTML = `
                <div class="log-meta">
                    <span>${new Date(log.timestamp).toLocaleString()}</span>
                    <span>路由: ${log.metadata.route_used}</span>
                    ${hasDraft ? '<span class="draft-badge">Hermes 建議待審</span>' : ''}
                </div>
                <div class="log-prompt">${userPrompt || '無提問'}</div>
            `;
            
            div.addEventListener('click', () => selectLog(index, hasDraft));
            logList.appendChild(div);
        });
    }

    function selectLog(index, hasDraft = false) {
        activeLogIndex = index;
        renderLogs();
        
        const log = currentLogs[index];
        const userMsg = log.messages.find(m => m.role === 'user');
        const astMsg = log.messages.find(m => m.role === 'assistant');
        const userPrompt = userMsg ? userMsg.content : '';
        
        editorPrompt.textContent = userPrompt;
        
        // If there's a draft, show the comparison
        if (hasDraft) {
            const draft = currentDrafts.find(d => d.original_interaction.messages[0].content === userPrompt);
            editorResponse.value = draft.hermes_suggestion;
            editorResponse.style.border = '2px solid var(--accent-color)';
            saveBtn.innerHTML = '✅ 批准 Hermes 修正版本';
        } else {
            editorResponse.value = astMsg ? astMsg.content : '';
            editorResponse.style.border = '1px solid rgba(255,255,255,0.1)';
            saveBtn.innerHTML = '驗證並儲存';
        }
        
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

    function shouldSkipFile(file) {
        const name = file.name.toLowerCase();
        const path = (file.webkitRelativePath || '').toLowerCase();
        
        // Blacklisted directories in relative path
        const ignoreDirs = ['node_modules/', '.git/', '.venv/', '__pycache__/', '.idea/', '.vscode/', 'dist/', 'build/', 'temp/', 'tmp/'];
        if (ignoreDirs.some(dir => path.includes(dir) || path.startsWith(dir))) {
            return true;
        }
        
        // Hidden files, temp files, or incomplete downloads
        if (name.startsWith('.') || name.startsWith('~$') || name.endsWith('.downloading') || name.endsWith('.crdownload') || name.endsWith('.part')) {
            return true;
        }
        
        // System files
        const ignoreFiles = ['thumbs.db', 'desktop.ini', '.ds_store'];
        if (ignoreFiles.includes(name)) {
            return true;
        }
        
        // Skip files larger than 1GB (backend limit is 1GB)
        if (file.size > 1024 * 1024 * 1024) {
            console.warn(`Skipping ${name}: file size exceeds 1GB limit.`);
            return true;
        }
        
        return false;
    }

    async function handleFiles(files) {
        if (!files.length) return;
        
        const fileArray = Array.from(files);
        const totalRaw = fileArray.length;
        
        // Filtering
        const toUpload = [];
        let skipCount = 0;
        
        for (const file of fileArray) {
            if (shouldSkipFile(file)) {
                skipCount++;
            } else {
                toUpload.push(file);
            }
        }
        
        const totalToUpload = toUpload.length;
        let successCount = 0;
        let failCount = 0;
        
        const dataType = document.getElementById('dataTypeSelect').value;
        
        // UI Elements
        const progressContainer = document.getElementById('uploadProgressContainer');
        const progressBar = document.getElementById('uploadProgressBar');
        const statsGrid = document.getElementById('uploadStatsGrid');
        const statSuccess = document.getElementById('statSuccess');
        const statFail = document.getElementById('statFail');
        const statSkip = document.getElementById('statSkip');
        const statPending = document.getElementById('statPending');
        
        // Reset and Show UI
        uploadStatus.innerHTML = '';
        progressBar.style.width = '0%';
        progressContainer.style.display = 'block';
        statsGrid.style.display = 'grid';
        
        statSuccess.textContent = '0';
        statFail.textContent = '0';
        statSkip.textContent = skipCount;
        statPending.textContent = totalToUpload;
        
        if (totalToUpload === 0) {
            uploadStatus.innerHTML = `<span style="color:#fbbf24">沒有需要上傳的檔案 (已跳過 ${skipCount} 個系統或無關檔案)。</span>`;
            progressBar.style.width = '100%';
            fileInput.value = '';
            folderInput.value = '';
            return;
        }
        
        // Upload sequentially for 100% reliability
        for (let i = 0; i < totalToUpload; i++) {
            const file = toUpload[i];
            const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
            
            uploadStatus.innerHTML = `<span style="color:var(--accent-color)">正在處理與上傳 (${i + 1} / ${totalToUpload}): <strong>${file.name}</strong> (${fileSizeMB} MB)</span>`;
            statPending.textContent = totalToUpload - i;
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('data_type', dataType);
            
            try {
                const res = await fetch('/api/dashboard/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (res.ok) {
                    const data = await res.json();
                    successCount += 1;
                    statSuccess.textContent = successCount;
                } else {
                    failCount += 1;
                    statFail.textContent = failCount;
                    console.error(`Upload failed for ${file.name}:`, res.statusText);
                }
            } catch (e) {
                failCount += 1;
                statFail.textContent = failCount;
                console.error(`Network error uploading ${file.name}:`, e);
            }
            
            // Update Progress Bar
            const percent = Math.round(((i + 1) / totalToUpload) * 100);
            progressBar.style.width = `${percent}%`;
            
            // Add a slight delay to prevent overwhelming the browser I/O or network stack
            await new Promise(r => setTimeout(r, 50));
        }
        
        statPending.textContent = '0';
        
        // Final Status
        if (failCount === 0) {
            uploadStatus.innerHTML = `<span style="color:#4ade80; font-weight: 600;">🎉 成功上傳所有 ${successCount} 個檔案！ (已跳過 ${skipCount} 個無關檔案)</span>`;
        } else {
            uploadStatus.innerHTML = `<span style="color:#f87171; font-weight: 600;">⚠️ 上傳完成。成功: ${successCount} 個，失敗: ${failCount} 個，已跳過: ${skipCount} 個。</span>`;
        }
        
        fileInput.value = '';
        folderInput.value = '';
    }

    // --- Tab 3: Live Chat ---
    const chatHistory = document.getElementById('chatHistory');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');

    function addMessageToChat(role, text, route = null) {
        const div = document.createElement('div');
        div.className = `message ${role === 'user' ? 'user-msg' : 'bot-msg'}`;
        
        // 使用 marked 解析 AI 的 Markdown 語法（粗體、清單、換行等）
        if (role === 'bot') {
            const contentDiv = document.createElement('div');
            contentDiv.className = 'markdown-content';
            contentDiv.innerHTML = marked.parse(text);
            div.appendChild(contentDiv);
        } else {
            div.textContent = text;
        }
        
        if (route) {
            const badge = document.createElement('span');
            badge.className = 'route-badge';
            badge.textContent = `經由 ${route}`;
            div.appendChild(badge);
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
        
        // Create an empty bot message container
        const div = document.createElement('div');
        div.className = 'message bot-msg';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'markdown-content';
        contentDiv.innerHTML = '<span class="typing-indicator">...</span>';
        div.appendChild(contentDiv);
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        let fullResponse = '';
        let routeUsed = null;

        try {
            const res = await fetch('/api/chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: 'dashboard_test_user',
                    message: text,
                    stream: true
                })
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop(); // Keep incomplete chunk in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6);
                        if (dataStr === '[DONE]') break;
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.route_used) {
                                routeUsed = data.route_used;
                                const badge = document.createElement('span');
                                badge.className = 'route-badge';
                                badge.textContent = `經由 ${routeUsed}`;
                                div.appendChild(badge);
                            }
                            if (data.content) {
                                fullResponse += data.content;
                                contentDiv.innerHTML = marked.parse(fullResponse);
                                chatHistory.scrollTop = chatHistory.scrollHeight;
                            }
                        } catch (e) {
                            console.warn("Parse error on stream chunk", e);
                        }
                    }
                }
            }
        } catch (e) {
            contentDiv.innerHTML = '與伺服器通訊時發生錯誤。';
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

    // --- OCR Log Polling ---
    const ocrLogContainer = document.getElementById('ocrLogContainer');
    let lastOcrLogIndex = 0;
    
    async function pollOcrLogs() {
        try {
            const res = await fetch(`/api/dashboard/ocr_logs?after=${lastOcrLogIndex}`);
            if (res.ok) {
                const data = await res.json();
                if (data.logs && data.logs.length > 0) {
                    if (lastOcrLogIndex === 0) {
                        ocrLogContainer.innerHTML = ''; // clear placeholder
                    }
                    data.logs.forEach(log => {
                        const div = document.createElement('div');
                        div.style.marginBottom = '4px';
                        
                        // Simple color coding based on log content
                        if (log.includes('✅')) {
                            div.style.color = '#4ade80';
                        } else if (log.includes('❌') || log.includes('⚠️')) {
                            div.style.color = '#f87171';
                        } else {
                            div.style.color = '#e5e7eb';
                        }
                        
                        div.textContent = log;
                        ocrLogContainer.appendChild(div);
                    });
                    
                    lastOcrLogIndex = data.next_index;
                    ocrLogContainer.scrollTop = ocrLogContainer.scrollHeight;
                }
            }
        } catch (e) {
            console.error("Failed to fetch OCR logs", e);
        }
    }
    
    // Poll every 1.5 seconds
    setInterval(pollOcrLogs, 1500);

    // Initial Load
    loadLogs();
});
