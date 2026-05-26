document.addEventListener('DOMContentLoaded', () => {
    console.log("Dashboard JS V12 (Optimized) Loading...");

    // --- Navigation Tabs ---
    const tabBtns = document.querySelectorAll('nav.nav-tabs .tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active-tab'));
            btn.classList.add('active');
            const targetId = `tab-${btn.dataset.tab}`;
            const targetEl = document.getElementById(targetId);
            if (targetEl) targetEl.classList.add('active-tab');
            
            if (btn.dataset.tab === 'curation') loadLogs();
            if (btn.dataset.tab === 'articles') loadArticles();
            if (btn.dataset.tab === 'analytics') loadAnalytics();
        });
    });

    window.copyToClipboard = (elementId) => {
        const el = document.getElementById(elementId);
        if (!el) return;
        el.select();
        document.execCommand('copy');
    };

    // --- Tab 1: Curation (Batch Workflow) ---
    const logList = document.getElementById('logList');
    const editorPanel = document.getElementById('editorPanel');
    const editorPrompt = document.getElementById('editorPrompt');
    const editorResponse = document.getElementById('editorResponse');
    const saveBtn = document.getElementById('saveBtn');
    const discardBtn = document.getElementById('discardBtn');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const batchSaveBtn = document.getElementById('batchSaveBtn');
    const evidencePanel = document.getElementById('evidencePanel');
    const evidenceContent = document.getElementById('evidenceContent');
    
    let currentLogs = [];
    let currentDrafts = []; 
    let proactiveQA = []; 
    let activeLogIndex = -1;
    let isActiveProactive = false;
    let pendingEdits = {}; // { "type_id": { prompt, response } }

    async function loadLogs() {
        if (logList) logList.innerHTML = '<div style="padding:20px; color:#666;">載入中...</div>';
        try {
            const [logsRes, draftsRes, proactiveRes] = await Promise.all([
                fetch('/api/dashboard/logs').then(r => r.ok ? r.json() : []),
                fetch('/api/dashboard/drafts').then(r => r.ok ? r.json() : []),
                fetch('/api/dashboard/proactive').then(r => r.ok ? r.json() : [])
            ]);
            currentLogs = logsRes || [];
            currentDrafts = draftsRes || [];
            proactiveQA = proactiveRes || [];
            renderLogs();
        } catch (e) { console.error("Load logs failed:", e); }
    }

    function _getItemKey(type, id) { return `${type}_${id}`; }

    function renderLogs() {
        if (!logList) return;
        logList.innerHTML = '';
        if (currentLogs.length === 0 && currentDrafts.length === 0 && proactiveQA.length === 0) {
            logList.innerHTML = '<div style="padding:20px; color:#666;">尚無待校正資料。</div>';
            return;
        }

        const createItem = (item, type, index, isProactive = false) => {
            const div = document.createElement('div');
            const userPrompt = isProactive ? item.question : (item.messages?.[0]?.content || '無提問');
            const itemId = isProactive ? item.question : item.timestamp;
            const key = _getItemKey(isProactive ? 'proactive' : type, itemId);
            const isSelected = !!pendingEdits[key];
            const hasDraft = !isProactive && currentDrafts.some(d => d.original_interaction?.messages[0]?.content === userPrompt);

            div.className = `log-item ${isProactive ? 'proactive-item' : ''} ${!isProactive && !isActiveProactive && index === activeLogIndex ? 'active' : ''} ${isActiveProactive && isProactive && index === activeLogIndex ? 'active' : ''} ${hasDraft ? 'has-draft' : ''}`;
            
            let metaHtml = '';
            if (isProactive) {
                metaHtml = `<span>模擬提問</span><span class="proactive-badge">🚀 ${item.service}</span>`;
            } else {
                const score = item.metadata?.confidence_score || 0;
                let sClass = score >= 85 ? 'score-high' : (score >= 60 ? 'score-mid' : 'score-low');
                metaHtml = `<span>${new Date(item.timestamp).toLocaleString()}</span><span class="score-badge ${sClass}">${score}%</span>${hasDraft ? '<span class="draft-badge">Hermes 建議</span>' : ''}`;
            }

            div.innerHTML = `
                <div style="display:flex; gap:10px; align-items:flex-start;">
                    <input type="checkbox" class="bulk-check" data-key="${key}" ${isSelected ? 'checked' : ''} style="margin-top:5px; transform: scale(1.2);">
                    <div style="flex:1;">
                        <div class="log-meta">${metaHtml}</div>
                        <div class="log-prompt">${userPrompt}</div>
                    </div>
                </div>`;

            div.querySelector('.bulk-check').addEventListener('click', (e) => {
                e.stopPropagation();
                if (e.target.checked) _saveCurrentToPending(isProactive, index);
                else delete pendingEdits[key];
            });

            div.addEventListener('click', () => {
                isActiveProactive = isProactive;
                if (isProactive) selectProactive(index); else selectLog(index, hasDraft);
            });
            return div;
        };

        proactiveQA.slice().reverse().forEach((p, i) => logList.appendChild(createItem(p, 'proactive', proactiveQA.length - 1 - i, true)));
        currentLogs.slice().reverse().forEach((l, i) => logList.appendChild(createItem(l, 'log', currentLogs.length - 1 - i, false)));
    }

    function _saveCurrentToPending(isProactive, index) {
        let type = 'log', id, prompt, response;
        if (isProactive) {
            const p = proactiveQA[index]; type = 'proactive'; id = p.question; prompt = p.question; response = p.answer;
        } else {
            const l = currentLogs[index]; id = l.timestamp; 
            const draft = currentDrafts.find(d => d.original_interaction?.messages[0]?.content === l.messages[0].content);
            if (draft) { type = 'draft'; id = draft.timestamp; response = draft.hermes_suggestion; }
            else { response = l.messages.find(m => m.role === 'assistant')?.content || ''; }
            prompt = l.messages[0].content;
        }
        pendingEdits[_getItemKey(type, id)] = { prompt, response, index, isProactive, type, id };
    }

    function selectLog(index, hasDraft = false) {
        _updatePendingFromEditor();
        activeLogIndex = index; renderLogs();
        const log = currentLogs[index]; if (!log) return;
        const userMsg = log.messages[0]; const astMsg = log.messages[1];
        const key = _getItemKey(hasDraft ? 'draft' : 'log', hasDraft ? currentDrafts.find(d => d.original_interaction?.messages[0]?.content === userMsg.content)?.timestamp : log.timestamp);
        
        if (pendingEdits[key]) {
            editorPrompt.value = pendingEdits[key].prompt; editorResponse.value = pendingEdits[key].response;
        } else {
            editorPrompt.value = userMsg ? userMsg.content : '';
            editorResponse.value = hasDraft ? currentDrafts.find(d => d.original_interaction?.messages[0]?.content === userMsg.content).hermes_suggestion : (astMsg ? astMsg.content : '');
        }
        
        if (hasDraft) {
            editorResponse.style.border = '2px solid var(--accent-color)';
            saveBtn.innerHTML = '✅ 批准並存入訓練集';
            const draft = currentDrafts.find(d => d.original_interaction?.messages[0]?.content === userMsg.content);
            if (evidencePanel && evidenceContent && draft?.search_results) {
                evidenceContent.innerHTML = draft.search_results.map(r => `
                    <div style="margin-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:8px;">
                        <div style="font-weight:600; color:#e2e8f0;">${r.title}</div><div>${r.body}</div><a href="${r.href}" target="_blank" style="color:#60a5fa; font-size:0.8rem;">查看來源 ↗</a>
                    </div>`).join('');
                evidencePanel.style.display = 'block';
            }
        } else {
            editorResponse.style.border = '1px solid rgba(255,255,255,0.1)';
            saveBtn.innerHTML = '✅ 驗證並儲存';
            if (evidencePanel) evidencePanel.style.display = 'none';
        }
        if (editorPanel) editorPanel.style.display = 'block';
    }

    function selectProactive(index) {
        _updatePendingFromEditor();
        isActiveProactive = true; activeLogIndex = index; renderLogs();
        const pqa = proactiveQA[index]; const key = _getItemKey('proactive', pqa.question);
        editorPrompt.value = pendingEdits[key] ? pendingEdits[key].prompt : pqa.question;
        editorResponse.value = pendingEdits[key] ? pendingEdits[key].response : pqa.answer;
        editorResponse.style.border = '2px solid #a855f7';
        saveBtn.innerHTML = '✅ 批准並存入訓練集';
        if (evidencePanel) evidencePanel.style.display = 'none';
        if (editorPanel) editorPanel.style.display = 'block';
    }

    function _updatePendingFromEditor() {
        if (activeLogIndex === -1) return;
        const key = _getActiveKey();
        if (pendingEdits[key]) {
            pendingEdits[key].prompt = editorPrompt.value;
            pendingEdits[key].response = editorResponse.value;
        }
    }

    function _getActiveKey() {
        if (activeLogIndex === -1) return null;
        if (isActiveProactive) return _getItemKey('proactive', proactiveQA[activeLogIndex].question);
        const log = currentLogs[activeLogIndex];
        const draft = currentDrafts.find(d => d.original_interaction?.messages[0]?.content === log.messages[0].content);
        return _getItemKey(draft ? 'draft' : 'log', draft ? draft.timestamp : log.timestamp);
    }

    if (selectAllBtn) selectAllBtn.addEventListener('click', () => {
        const anyUnchecked = Array.from(document.querySelectorAll('.bulk-check')).some(c => !c.checked);
        if (anyUnchecked) {
            proactiveQA.forEach((p, i) => _saveCurrentToPending(true, i));
            currentLogs.forEach((l, i) => _saveCurrentToPending(false, i));
        } else pendingEdits = {};
        renderLogs();
    });

    if (batchSaveBtn) batchSaveBtn.addEventListener('click', async () => {
        const keys = Object.keys(pendingEdits);
        if (keys.length === 0) { alert("請先勾選項目。"); return; }
        if (!confirm(`批量儲存 ${keys.length} 筆資料？`)) return;
        batchSaveBtn.textContent = '處理中...';
        let success = 0;
        for (const key of keys) {
            const item = pendingEdits[key];
            try {
                const res = await fetch('/api/dashboard/logs/correct', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        original_log: item.isProactive ? { messages: [{role:'user', content:item.prompt}] } : currentLogs[item.index],
                        corrected_prompt: item.prompt, corrected_response: item.response,
                        item_type: item.type, item_id: item.id
                    })
                });
                if (res.ok) success++;
            } catch (e) {}
        }
        alert(`完成！成功: ${success} 筆。`);
        pendingEdits = {}; activeLogIndex = -1; editorPanel.style.display = 'none';
        loadLogs(); batchSaveBtn.textContent = '批量儲存已選';
    });

    if (saveBtn) saveBtn.addEventListener('click', async () => {
        if (activeLogIndex === -1) return;
        _updatePendingFromEditor();
        const key = _getActiveKey();
        const item = pendingEdits[key] || { prompt: editorPrompt.value, response: editorResponse.value, isProactive: isActiveProactive };
        saveBtn.textContent = '儲存中...';
        try {
            const res = await fetch('/api/dashboard/logs/correct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_log: isActiveProactive ? { messages: [{role:'user',content:proactiveQA[activeLogIndex].question}] } : currentLogs[activeLogIndex],
                    corrected_prompt: item.prompt, corrected_response: item.response,
                    item_type: isActiveProactive ? 'proactive' : (currentDrafts.some(d=>d.original_interaction?.messages[0]?.content === currentLogs[activeLogIndex].messages[0].content) ? 'draft' : 'log'),
                    item_id: isActiveProactive ? proactiveQA[activeLogIndex].question : currentLogs[activeLogIndex].timestamp
                })
            });
            if (res.ok) { delete pendingEdits[key]; activeLogIndex = -1; editorPanel.style.display = 'none'; loadLogs(); }
        } catch (e) {} finally { saveBtn.textContent = '驗證並儲存'; }
    });

    if (discardBtn) discardBtn.addEventListener('click', async () => {
        if (activeLogIndex === -1) return;
        if (!confirm('捨棄此項目？')) return;
        const key = _getActiveKey();
        const type = isActiveProactive ? 'proactive' : (currentDrafts.some(d=>d.original_interaction?.messages[0]?.content === currentLogs[activeLogIndex].messages[0].content) ? 'draft' : 'log');
        const id = isActiveProactive ? proactiveQA[activeLogIndex].question : currentLogs[activeLogIndex].timestamp;
        try {
            const res = await fetch('/api/dashboard/logs/discard', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ item_type: type, item_id: id }) });
            if (res.ok) { delete pendingEdits[key]; activeLogIndex = -1; editorPanel.style.display = 'none'; loadLogs(); }
        } catch (e) {}
    });

    // --- Tab 4: Article Sync ---
    const articleList = document.getElementById('articleList');
    const articleEditorPanel = document.getElementById('articleEditorPanel');
    const articleTitle = document.getElementById('articleTitle');
    const articleCategory = document.getElementById('articleCategory');
    const articleContent = document.getElementById('articleContent');
    const markSyncedBtn = document.getElementById('markSyncedBtn');
    let currentArticles = []; let activeArticleIndex = -1;
    async function loadArticles() {
        if (articleList) articleList.innerHTML = '<div>載入中...</div>';
        try { const res = await fetch('/api/dashboard/articles'); currentArticles = await res.json(); renderArticles(); } catch (e) {}
    }
    function renderArticles() {
        if (!articleList) return; articleList.innerHTML = '';
        if (currentArticles.length === 0) { articleList.innerHTML = '<div style="padding:20px; color:#666;">無資料。</div>'; return; }
        currentArticles.forEach((art, index) => {
            const div = document.createElement('div'); div.className = `log-item ${index === activeArticleIndex ? 'active' : ''}`;
            div.innerHTML = `<div class="log-meta"><span>類別: ${art.category}</span></div><div class="log-prompt">${art.title}</div>`;
            div.addEventListener('click', () => { activeArticleIndex = index; renderArticles(); articleTitle.value = art.title; articleCategory.value = art.category; articleContent.value = art.content; articleEditorPanel.style.display = 'block'; });
            articleList.appendChild(div);
        });
    }
    if (markSyncedBtn) markSyncedBtn.addEventListener('click', async () => {
        const art = currentArticles[activeArticleIndex];
        try {
            const res = await fetch('/api/dashboard/articles/sync', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: art.title }) });
            if (res.ok) { currentArticles.splice(activeArticleIndex, 1); activeArticleIndex = -1; articleEditorPanel.style.display = 'none'; renderArticles(); }
        } catch (e) {}
    });

    // --- Tab 5: Analytics (BI Dashboard) ---
    let proceduresChart = null;
    let painPointsChart = null;

    async function loadAnalytics() {
        try {
            const res = await fetch('/api/dashboard/analytics');
            const data = await res.json();
            
            const ctx1 = document.getElementById('proceduresChart').getContext('2d');
            if (proceduresChart) proceduresChart.destroy();
            proceduresChart = new Chart(ctx1, {
                type: 'bar',
                data: {
                    labels: data.top_procedures.map(p => p.name),
                    datasets: [{
                        label: '詢問次數',
                        data: data.top_procedures.map(p => p.count),
                        backgroundColor: 'rgba(56, 189, 248, 0.4)',
                        borderColor: '#38bdf8',
                        borderWidth: 2,
                        borderRadius: 8
                    }]
                },
                options: { 
                    responsive: true, maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }, x: { ticks: { color: '#94a3b8' } } },
                    plugins: { legend: { display: false } }
                }
            });

            const ctx2 = document.getElementById('painPointsChart').getContext('2d');
            if (painPointsChart) painPointsChart.destroy();
            painPointsChart = new Chart(ctx2, {
                type: 'doughnut',
                data: {
                    labels: data.pain_points.map(p => p.name),
                    datasets: [{
                        data: data.pain_points.map(p => p.count),
                        backgroundColor: ['#38bdf8', '#818cf8', '#a855f7', '#f472b6', '#fb7185'],
                        borderWidth: 0,
                        hoverOffset: 10
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', padding: 20 } } } }
            });
        } catch (e) { console.error("Load analytics failed:", e); }
    }

    // --- Tab 2: Upload Data ---
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const folderInput = document.getElementById('folderInput');
    const uploadStatus = document.getElementById('uploadStatus');
    if (document.getElementById('btnSelectFiles')) document.getElementById('btnSelectFiles').addEventListener('click', () => fileInput.click());
    if (document.getElementById('btnSelectFolder')) document.getElementById('btnSelectFolder').addEventListener('click', () => folderInput.click());
    if (dropzone) {
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => { e.preventDefault(); dropzone.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
    }
    if (fileInput) fileInput.addEventListener('change', () => handleFiles(fileInput.files));
    if (folderInput) folderInput.addEventListener('change', () => handleFiles(folderInput.files));
    async function handleFiles(files) {
        if (!files.length) return;
        const fileArray = Array.from(files).filter(f => !f.name.startsWith('.') && !f.name.startsWith('~$'));
        const totalToUpload = fileArray.length;
        let successCount = 0, failCount = 0;
        const dataType = document.getElementById('dataTypeSelect').value;
        const progressContainer = document.getElementById('uploadProgressContainer');
        if (progressContainer) progressContainer.style.display = 'block';
        for (let i = 0; i < totalToUpload; i++) {
            const file = fileArray[i];
            if (uploadStatus) uploadStatus.innerHTML = `正在上傳 (${i+1}/${totalToUpload}): ${file.name}`;
            try {
                const base64Data = await new Promise((resolve, reject) => {
                    const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = reject; reader.readAsDataURL(file);
                });
                const res = await fetch('/api/dashboard/upload_base64', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ filename: file.name, file_data: base64Data, data_type: dataType }) });
                if (res.ok) { successCount++; document.getElementById('statSuccess').textContent = successCount; } else { throw new Error('Fail'); }
            } catch (e) { failCount++; document.getElementById('statFail').textContent = failCount; }
            document.getElementById('uploadProgressBar').style.width = `${Math.round(((i + 1) / totalToUpload) * 100)}%`;
            document.getElementById('statPending').textContent = totalToUpload - (i + 1);
            await new Promise(r => setTimeout(r, 100));
        }
        if (uploadStatus) uploadStatus.innerHTML = failCount === 0 ? '🎉 全部完成！' : `⚠️ 完畢。失敗: ${failCount}`;
        if (fileInput) fileInput.value = ''; if (folderInput) folderInput.value = '';
    }

    // --- Tab 3: Live Chat with SSE & Score ---
    const chatHistory = document.getElementById('chatHistory');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatImageInput = document.getElementById('chatImageInput');
    const chatImagePreview = document.getElementById('chatImagePreview');
    let currentBase64Image = null;
    if (document.getElementById('chatUploadBtn')) document.getElementById('chatUploadBtn').addEventListener('click', () => chatImageInput.click());
    if (chatImageInput) chatImageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader(); reader.onload = (re) => { currentBase64Image = re.target.result.split(',')[1]; document.getElementById('previewImg').src = re.target.result; chatImagePreview.style.display = 'block'; }; reader.readAsDataURL(file);
        }
    });
    if (document.getElementById('clearImageBtn')) document.getElementById('clearImageBtn').addEventListener('click', () => { currentBase64Image = null; chatImageInput.value = ''; chatImagePreview.style.display = 'none'; });
    function addMessageToChat(role, text, route = null, isHighRisk = false, confidenceScore = null) {
        if (!chatHistory) return;
        const div = document.createElement('div'); div.className = `message ${role === 'user' ? 'user-msg' : 'bot-msg'} ${isHighRisk ? 'risk-alert' : ''}`;
        if (isHighRisk) { const badge = document.createElement('div'); badge.className = 'risk-badge'; badge.textContent = '🚨 高風險警告'; div.appendChild(badge); }
        const contentDiv = document.createElement('div'); contentDiv.className = 'markdown-content';
        if (role === 'bot') { if (typeof marked !== 'undefined') contentDiv.innerHTML = marked.parse(text); else contentDiv.textContent = text; }
        else { contentDiv.textContent = text; }
        div.appendChild(contentDiv);
        const footer = document.createElement('div'); footer.style.cssText = 'display:flex; justify-content:flex-end; gap:10px; margin-top:10px; opacity:0.6; font-size:0.7rem; font-family:Outfit;';
        if (confidenceScore !== null) { let sClass = confidenceScore >= 85 ? 'score-high' : (confidenceScore >= 60 ? 'score-mid' : 'score-low'); footer.innerHTML += `<span class="score-badge ${sClass}">🎯 ${confidenceScore}%</span>`; }
        if (route) footer.innerHTML += `<span class="route-badge" style="position:static;">經由 ${route}</span>`;
        div.appendChild(footer); chatHistory.appendChild(div); chatHistory.scrollTop = chatHistory.scrollHeight; return div;
    }
    async function sendMessage() {
        if (!chatInput) return; const text = chatInput.value.trim(); if (!text && !currentBase64Image) return;
        addMessageToChat('user', text); if (currentBase64Image) { const imgDiv = document.createElement('div'); imgDiv.className = 'message user-msg'; imgDiv.innerHTML = `<img src="data:image/jpeg;base64,${currentBase64Image}" style="max-width:200px; border-radius:8px;">`; chatHistory.appendChild(imgDiv); }
        const imageToSend = currentBase64Image; chatInput.value = ''; currentBase64Image = null; chatImagePreview.style.display = 'none';
        chatInput.disabled = true; chatSendBtn.disabled = true;
        const div = document.createElement('div'); div.className = 'message bot-msg';
        const contentDiv = document.createElement('div'); contentDiv.className = 'markdown-content'; contentDiv.innerHTML = '<span class="typing-indicator">...</span>';
        div.appendChild(contentDiv); const footer = document.createElement('div'); footer.style.cssText = 'display:flex; justify-content:flex-end; gap:10px; margin-top:10px; opacity:0.6; font-size:0.7rem; font-family:Outfit;'; div.appendChild(footer);
        chatHistory.appendChild(div); chatHistory.scrollTop = chatHistory.scrollHeight;
        let fullResponse = '';
        try {
            const res = await fetch('/api/chat/message', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: 'dashboard_user', message: text, stream: true, image: imageToSend }) });
            const reader = res.body.getReader(); const decoder = new TextDecoder('utf-8'); let buffer = '';
            while (true) {
                const { done, value } = await reader.read(); if (done) break;
                buffer += decoder.decode(value, { stream: true }); const lines = buffer.split('\n\n'); buffer = lines.pop();
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6); if (dataStr === '[DONE]') break;
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.is_high_risk) { div.classList.add('risk-alert'); }
                            if (data.route_used) { if (!footer.innerHTML.includes('經由')) footer.innerHTML += `<span class="route-badge" style="position:static;">經由 ${data.route_used}</span>`; }
                            if (data.confidence_score !== undefined) { let sClass = data.confidence_score >= 85 ? 'score-high' : (data.confidence_score >= 60 ? 'score-mid' : 'score-low'); footer.innerHTML = `<span class="score-badge ${sClass}">🎯 ${data.confidence_score}%</span>` + footer.innerHTML; }
                            if (data.content) { fullResponse += data.content; if (typeof marked !== 'undefined') contentDiv.innerHTML = marked.parse(fullResponse); else contentDiv.textContent = fullResponse; chatHistory.scrollTop = chatHistory.scrollHeight; }
                        } catch (e) {}
                    }
                }
            }
        } catch (e) {} finally { chatInput.disabled = false; chatSendBtn.disabled = false; chatInput.focus(); }
    }
    if (chatSendBtn) chatSendBtn.addEventListener('click', sendMessage);
    if (chatInput) chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

    // --- OCR Polling ---
    let lastOcrLogIndex = 0;
    setInterval(async () => {
        const ocrLogContainer = document.getElementById('ocrLogContainer'); if (!ocrLogContainer) return;
        try {
            const res = await fetch(`/api/dashboard/ocr_logs?after=${lastOcrLogIndex}`); if (!res.ok) return;
            const data = await res.json();
            if (data.logs && data.logs.length > 0) {
                if (lastOcrLogIndex === 0) ocrLogContainer.innerHTML = '';
                data.logs.forEach(log => {
                    const div = document.createElement('div'); div.style.marginBottom = '4px';
                    if (log.includes('✅')) div.style.color = '#4ade80'; else if (log.includes('❌') || log.includes('⚠️')) div.style.color = '#f87171'; else div.style.color = '#e5e7eb';
                    div.textContent = log; ocrLogContainer.appendChild(div);
                });
                lastOcrLogIndex = data.next_index; ocrLogContainer.scrollTop = ocrLogContainer.scrollHeight;
            }
        } catch (e) {}
    }, 1500);

    loadLogs();
});
