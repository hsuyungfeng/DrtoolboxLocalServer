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
            if (btn.dataset.tab === 'articles') loadArticles();
        });
    });

    // --- Global Helpers ---
    window.copyToClipboard = (elementId) => {
        const el = document.getElementById(elementId);
        el.select();
        document.execCommand('copy');
    };

    // --- Tab 1: Curation ---
    const logList = document.getElementById('logList');
    const editorPanel = document.getElementById('editorPanel');
    const editorPrompt = document.getElementById('editorPrompt');
    const editorResponse = document.getElementById('editorResponse');
    const saveBtn = document.getElementById('saveBtn');
    const discardBtn = document.getElementById('discardBtn');
    const exportBtn = document.getElementById('exportBtn');
    const triggerFactCheckBtn = document.getElementById('triggerFactCheckBtn');

    const evidencePanel = document.createElement('div');
    evidencePanel.id = 'evidencePanel';
    evidencePanel.style.cssText = 'display: none; margin-bottom: 20px; padding: 15px; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 12px;';
    evidencePanel.innerHTML = '<h3 style="font-size: 0.9rem; color: #60a5fa; margin-bottom: 8px;">🌐 Hermes 網路搜尋證據 (查證來源)</h3><div id="evidenceContent" style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;"></div>';
    editorPanel.insertBefore(evidencePanel, editorPanel.firstChild.nextSibling.nextSibling);
    const evidenceContent = document.getElementById('evidenceContent');
    
    let currentLogs = [];
    let currentDrafts = []; 
    let proactiveQA = []; 
    let activeLogIndex = -1;
    let isActiveProactive = false;

    async function loadLogs() {
        try {
            const [logsRes, draftsRes, proactiveRes] = await Promise.all([
                fetch('/api/dashboard/logs'),
                fetch('/api/dashboard/drafts'),
                fetch('/api/dashboard/proactive')
            ]);
            currentLogs = await logsRes.json();
            currentDrafts = await draftsRes.json();
            proactiveQA = await proactiveRes.json();
            renderLogs();
        } catch (e) { console.error(e); }
    }

    function renderLogs() {
        logList.innerHTML = '';
        proactiveQA.slice().reverse().forEach((pqa, reversedIndex) => {
            const index = proactiveQA.length - 1 - reversedIndex;
            const div = document.createElement('div');
            div.className = `log-item proactive-item ${isActiveProactive && index === activeLogIndex ? 'active' : ''}`;
            div.innerHTML = `
                <div class="log-meta">
                    <span>模擬提問</span>
                    <span class="proactive-badge">🚀 Proactive: ${pqa.service}</span>
                </div>
                <div class="log-prompt">${pqa.question}</div>
            `;
            div.addEventListener('click', () => selectProactive(index));
            logList.appendChild(div);
        });

        currentLogs.slice().reverse().forEach((log, reversedIndex) => {
            const index = currentLogs.length - 1 - reversedIndex;
            const userMsg = log.messages.find(m => m.role === 'user');
            const userPrompt = userMsg ? userMsg.content : '';
            const hasDraft = currentDrafts.some(d => d.original_interaction.messages[0].content === userPrompt);

            const div = document.createElement('div');
            div.className = `log-item ${!isActiveProactive && index === activeLogIndex ? 'active' : ''} ${hasDraft ? 'has-draft' : ''}`;
            div.innerHTML = `
                <div class="log-meta">
                    <span>${new Date(log.timestamp).toLocaleString()}</span>
                    <span>路由: ${log.metadata.route_used}</span>
                    ${hasDraft ? '<span class="draft-badge">Hermes 建議待審</span>' : ''}
                </div>
                <div class="log-prompt">${userPrompt || '無提問'}</div>
            `;
            div.addEventListener('click', () => { isActiveProactive = false; selectLog(index, hasDraft); });
            logList.appendChild(div);
        });
    }

    function selectLog(index, hasDraft = false) {
        activeLogIndex = index; renderLogs();
        const log = currentLogs[index];
        const userMsg = log.messages.find(m => m.role === 'user');
        const astMsg = log.messages.find(m => m.role === 'assistant');
        editorPrompt.value = userMsg ? userMsg.content : '';
        
        if (hasDraft) {
            const draft = currentDrafts.find(d => d.original_interaction.messages[0].content === editorPrompt.value);
            editorResponse.value = draft.hermes_suggestion;
            editorResponse.style.border = '2px solid var(--accent-color)';
            saveBtn.innerHTML = '✅ 批准 Hermes 修正版本';
            if (draft.search_results && draft.search_results.length > 0) {
                evidenceContent.innerHTML = draft.search_results.map(r => `
                    <div style="margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px;">
                        <div style="font-weight: 600; color: #e2e8f0; font-size: 0.9rem;">${r.title}</div>
                        <div style="margin: 4px 0;">${r.body}</div>
                        <a href="${r.href}" target="_blank" style="color: #60a5fa; text-decoration: none; font-size: 0.8rem;">查看來源 ↗</a>
                    </div>`).join('');
                evidencePanel.style.display = 'block';
            } else { evidencePanel.style.display = 'none'; }
        } else {
            editorResponse.value = astMsg ? astMsg.content : '';
            editorResponse.style.border = '1px solid rgba(255,255,255,0.1)';
            saveBtn.innerHTML = '驗證並儲存';
            evidencePanel.style.display = 'none';
        }
        editorPanel.style.display = 'block';
    }

    function selectProactive(index) {
        isActiveProactive = true; activeLogIndex = index; renderLogs();
        const pqa = proactiveQA[index];
        editorPrompt.value = pqa.question;
        editorResponse.value = pqa.answer;
        editorResponse.style.border = '2px solid #a855f7';
        saveBtn.innerHTML = '✅ 批准並存入訓練集';
        evidencePanel.style.display = 'none';
        editorPanel.style.display = 'block';
    }

    saveBtn.addEventListener('click', async () => {
        if (activeLogIndex === -1) return;
        let originalLog, correctedText, correctedPrompt, itemType, itemId;
        correctedPrompt = editorPrompt.value; correctedText = editorResponse.value;
        if (isActiveProactive) {
            const pqa = proactiveQA[activeLogIndex];
            originalLog = { messages: [{role: 'user', content: pqa.question}], metadata: { type: 'proactive', service: pqa.service } };
            itemType = 'proactive'; itemId = pqa.question;
        } else {
            originalLog = currentLogs[activeLogIndex];
            const draft = currentDrafts.find(d => d.original_interaction.messages[0].content === originalLog.messages[0].content);
            if (draft) { itemType = 'draft'; itemId = draft.timestamp; }
        }
        saveBtn.textContent = '儲存中...';
        try {
            const res = await fetch('/api/dashboard/logs/correct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ original_log: originalLog, corrected_prompt: correctedPrompt, corrected_response: correctedText, item_type: itemType, item_id: itemId })
            });
            if (res.ok) { _removeItemFromLocal(itemType, itemId); activeLogIndex = -1; editorPanel.style.display = 'none'; renderLogs(); }
        } catch (e) { console.error(e); } finally { saveBtn.textContent = '驗證並儲存'; }
    });

    discardBtn.addEventListener('click', async () => {
        if (activeLogIndex === -1) return;
        if (!confirm('確定要捨棄此項目嗎？')) return;
        let itemType, itemId;
        if (isActiveProactive) { itemType = 'proactive'; itemId = proactiveQA[activeLogIndex].question; }
        else {
            const log = currentLogs[activeLogIndex];
            const draft = currentDrafts.find(d => d.original_interaction.messages[0].content === log.messages[0].content);
            if (draft) { itemType = 'draft'; itemId = draft.timestamp; }
        }
        if (!itemType) { activeLogIndex = -1; editorPanel.style.display = 'none'; renderLogs(); return; }
        discardBtn.textContent = '移除中...';
        try {
            const res = await fetch('/api/dashboard/logs/discard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_type: itemType, item_id: itemId })
            });
            if (res.ok) { _removeItemFromLocal(itemType, itemId); activeLogIndex = -1; editorPanel.style.display = 'none'; renderLogs(); }
        } catch (e) { console.error(e); } finally { discardBtn.textContent = '🗑️ 捨棄此項目'; }
    });

    function _removeItemFromLocal(type, id) {
        if (isActiveProactive) proactiveQA.splice(activeLogIndex, 1);
        else if (type === 'draft') { const idx = currentDrafts.findIndex(d => d.timestamp === id); if (idx !== -1) currentDrafts.splice(idx, 1); }
    }

    exportBtn.addEventListener('click', () => { window.location.href = '/api/dashboard/export'; });
    if (triggerFactCheckBtn) {
        triggerFactCheckBtn.addEventListener('click', async () => {
            triggerFactCheckBtn.textContent = '⌛ 正在排程...'; triggerFactCheckBtn.disabled = true;
            try { const res = await fetch('/api/dashboard/drafts/trigger', { method: 'POST' }); if (res.ok) alert('任務已啟動！'); }
            catch (e) { console.error(e); } finally { triggerFactCheckBtn.textContent = '🔍 執行今日網實核查'; triggerFactCheckBtn.disabled = false; }
        });
    }

    // --- Tab 4: Article Sync ---
    const articleList = document.getElementById('articleList');
    const articleEditorPanel = document.getElementById('articleEditorPanel');
    const articleTitle = document.getElementById('articleTitle');
    const articleCategory = document.getElementById('articleCategory');
    const articleContent = document.getElementById('articleContent');
    const markSyncedBtn = document.getElementById('markSyncedBtn');
    const copyTitleBtn = document.getElementById('copyTitleBtn');
    const copyContentBtn = document.getElementById('copyContentBtn');

    let currentArticles = [];
    let activeArticleIndex = -1;

    async function loadArticles() {
        try {
            const res = await fetch('/api/dashboard/articles');
            currentArticles = await res.json();
            renderArticles();
        } catch (e) { console.error(e); }
    }

    function renderArticles() {
        articleList.innerHTML = '';
        currentArticles.forEach((art, index) => {
            const div = document.createElement('div');
            div.className = `log-item ${index === activeArticleIndex ? 'active' : ''}`;
            div.innerHTML = `
                <div class="log-meta">
                    <span>類別: ${art.category}</span>
                </div>
                <div class="log-prompt">${art.title}</div>
            `;
            div.addEventListener('click', () => selectArticle(index));
            articleList.appendChild(div);
        });
    }

    function selectArticle(index) {
        activeArticleIndex = index; renderArticles();
        const art = currentArticles[index];
        articleTitle.value = art.title;
        articleCategory.value = art.category;
        articleContent.value = art.content;
        articleEditorPanel.style.display = 'block';
    }

    copyTitleBtn.addEventListener('click', () => copyToClipboard('articleTitle'));
    copyContentBtn.addEventListener('click', () => copyToClipboard('articleContent'));

    markSyncedBtn.addEventListener('click', async () => {
        if (activeArticleIndex === -1) return;
        const art = currentArticles[activeArticleIndex];
        try {
            const res = await fetch('/api/dashboard/articles/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: art.title })
            });
            if (res.ok) {
                currentArticles.splice(activeArticleIndex, 1);
                activeArticleIndex = -1;
                articleEditorPanel.style.display = 'none';
                renderArticles();
            }
        } catch (e) { console.error(e); }
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
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (e) => { e.preventDefault(); dropzone.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
    fileInput.addEventListener('change', () => handleFiles(fileInput.files));
    folderInput.addEventListener('change', () => handleFiles(folderInput.files));

    async function handleFiles(files) {
        if (!files.length) return;
        const fileArray = Array.from(files);
        const toUpload = fileArray.filter(f => !f.name.startsWith('.'));
        const dataType = document.getElementById('dataTypeSelect').value;
        const progressContainer = document.getElementById('uploadProgressContainer');
        const progressBar = document.getElementById('uploadProgressBar');
        const statSuccess = document.getElementById('statSuccess');
        const statFail = document.getElementById('statFail');
        
        progressContainer.style.display = 'block';
        let success = 0, fail = 0;
        for (let i = 0; i < toUpload.length; i++) {
            const file = toUpload[i];
            uploadStatus.innerHTML = `正在上傳: ${file.name}`;
            const formData = new FormData();
            formData.append('file', file);
            formData.append('data_type', dataType);
            try {
                const res = await fetch('/api/dashboard/upload', { method: 'POST', body: formData });
                if (res.ok) success++; else fail++;
            } catch (e) { fail++; }
            progressBar.style.width = `${Math.round(((i + 1) / toUpload.length) * 100)}%`;
            statSuccess.textContent = success; statFail.textContent = fail;
        }
        uploadStatus.innerHTML = fail === 0 ? '🎉 上傳成功！' : '⚠️ 上傳完成，部分失敗。';
    }

    // --- Tab 3: Live Chat with Vision ---
    const chatHistory = document.getElementById('chatHistory');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatUploadBtn = document.getElementById('chatUploadBtn');
    const chatImageInput = document.getElementById('chatImageInput');
    const chatImagePreview = document.getElementById('chatImagePreview');
    const previewImg = document.getElementById('previewImg');
    const clearImageBtn = document.getElementById('clearImageBtn');

    let currentBase64Image = null;

    chatUploadBtn.addEventListener('click', () => chatImageInput.click());
    chatImageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (re) => {
                currentBase64Image = re.target.result.split(',')[1];
                previewImg.src = re.target.result;
                chatImagePreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });

    clearImageBtn.addEventListener('click', () => {
        currentBase64Image = null;
        chatImageInput.value = '';
        chatImagePreview.style.display = 'none';
    });

    function addMessageToChat(role, text, route = null) {
        const div = document.createElement('div');
        div.className = `message ${role === 'user' ? 'user-msg' : 'bot-msg'}`;
        if (role === 'bot') {
            const contentDiv = document.createElement('div');
            contentDiv.className = 'markdown-content';
            contentDiv.innerHTML = marked.parse(text);
            div.appendChild(contentDiv);
        } else { div.textContent = text; }
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
        if (!text && !currentBase64Image) return;
        
        addMessageToChat('user', text);
        if (currentBase64Image) {
            const imgDiv = document.createElement('div');
            imgDiv.className = 'message user-msg';
            imgDiv.innerHTML = `<img src="data:image/jpeg;base64,${currentBase64Image}" style="max-width: 200px; border-radius: 8px;">`;
            chatHistory.appendChild(imgDiv);
        }

        const imageToSend = currentBase64Image;
        // Reset inputs
        chatInput.value = ''; currentBase64Image = null; chatImagePreview.style.display = 'none';
        chatInput.disabled = true; chatSendBtn.disabled = true;
        
        const div = document.createElement('div');
        div.className = 'message bot-msg';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'markdown-content';
        contentDiv.innerHTML = '<span class="typing-indicator">...</span>';
        div.appendChild(contentDiv);
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        let fullResponse = '';
        try {
            const res = await fetch('/api/chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: 'dashboard_user', message: text, stream: true, image: imageToSend })
            });
            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6);
                        if (dataStr === '[DONE]') break;
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.route_used) {
                                const badge = document.createElement('span');
                                badge.className = 'route-badge';
                                badge.textContent = `經由 ${data.route_used}`;
                                div.appendChild(badge);
                            }
                            if (data.content) {
                                fullResponse += data.content;
                                contentDiv.innerHTML = marked.parse(fullResponse);
                                chatHistory.scrollTop = chatHistory.scrollHeight;
                            }
                        } catch (e) {}
                    }
                }
            }
        } catch (e) { contentDiv.innerHTML = '錯誤。'; }
        finally { chatInput.disabled = false; chatSendBtn.disabled = false; chatInput.focus(); }
    }

    chatSendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

    // --- OCR Log Polling ---
    const ocrLogContainer = document.getElementById('ocrLogContainer');
    let lastOcrLogIndex = 0;
    async function pollOcrLogs() {
        try {
            const res = await fetch(`/api/dashboard/ocr_logs?after=${lastOcrLogIndex}`);
            if (res.ok) {
                const data = await res.json();
                if (data.logs && data.logs.length > 0) {
                    if (lastOcrLogIndex === 0) ocrLogContainer.innerHTML = '';
                    data.logs.forEach(log => {
                        const div = document.createElement('div');
                        div.style.marginBottom = '4px';
                        if (log.includes('✅')) div.style.color = '#4ade80';
                        else if (log.includes('❌') || log.includes('⚠️')) div.style.color = '#f87171';
                        else div.style.color = '#e5e7eb';
                        div.textContent = log;
                        ocrLogContainer.appendChild(div);
                    });
                    lastOcrLogIndex = data.next_index;
                    ocrLogContainer.scrollTop = ocrLogContainer.scrollHeight;
                }
            }
        } catch (e) {}
    }
    setInterval(pollOcrLogs, 1500);
    loadLogs();
});
