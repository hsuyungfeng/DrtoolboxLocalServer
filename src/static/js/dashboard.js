document.addEventListener('DOMContentLoaded', () => {
    console.log("Dashboard JS V13 (Advanced Reasoning) Loading...");

    // --- Navigation Tabs ---
    const tabBtns = document.querySelectorAll('nav.nav-tabs .tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabName = btn.dataset.tab;
            if (tabName === 'setup') {
                return; // Let inline onclick redirect to /dashboard/setup/
            }
            console.log("Switching to tab:", tabName);
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => {
                c.style.display = 'none';
                c.classList.remove('active-tab');
            });

            btn.classList.add('active');
            const targetId = `tab-${tabName}`;
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                if (tabName === 'analytics') {
                    targetEl.style.display = 'grid';
                } else if (['upload', 'chat', 'knowledge-map'].includes(tabName)) {
                    targetEl.style.display = 'flex';
                } else {
                    targetEl.style.display = 'block';
                }
                targetEl.classList.add('active-tab');
            }
            
            if (tabName === 'curation') loadLogs();
            if (tabName === 'articles') loadArticles();
            if (tabName === 'analytics') loadAnalytics();
            if (tabName === 'knowledge-map') {
                setTimeout(loadKnowledgeGraph, 100);
            }
        });
    });

    window.copyToClipboard = (elementId) => {
        const el = document.getElementById(elementId);
        if (!el) return;
        el.select();
        document.execCommand('copy');
    };

    window.sendB2bEmail = async (companyId) => {
        try {
            const res = await fetch('/api/dashboard/analytics/b2b/dispatch_channel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ company_id: companyId })
            });
            const data = await res.json();
            if (data.success) {
                alert(`✅ 成功經由 [${data.sent_channel}] 管道為 ${companyId} 觸發特約開拓推播！`);
                loadAnalytics();
            } else {
                alert(`發送失敗: ${data.error || '未知錯誤'}`);
            }
        } catch (e) {
            alert(`發送失敗: ${e.message}`);
        }
    };

    // --- Header Actions ---
    const triggerFactCheckBtn = document.getElementById('triggerFactCheckBtn');
    const exportBtn = document.getElementById('exportBtn');

    // --- SOAP Voice & Dual LLM Lab Actions ---
    const startVoiceRecordBtn = document.getElementById('startVoiceRecordBtn');
    const runPatientOcrBtn = document.getElementById('runPatientOcrBtn');
    const runSoapCompareBtn = document.getElementById('runSoapCompareBtn');

    if (startVoiceRecordBtn) {
        let isRecording = false;
        startVoiceRecordBtn.addEventListener('click', async () => {
            if (!isRecording) {
                isRecording = true;
                startVoiceRecordBtn.textContent = '⏹️ 停止錄音 (辨識中)';
                startVoiceRecordBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';

                // 自動觸發 OCR 解析螢幕
                if (runPatientOcrBtn) runPatientOcrBtn.click();
            } else {
                isRecording = false;
                startVoiceRecordBtn.textContent = '🎙️ 開始錄音 (觸發 OCR)';
                startVoiceRecordBtn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
            }
        });
    }

    if (runPatientOcrBtn) {
        runPatientOcrBtn.addEventListener('click', async () => {
            runPatientOcrBtn.disabled = true;
            runPatientOcrBtn.textContent = '⏳ OCR 辨識中...';
            try {
                const res = await fetch('/api/dashboard/soap/ocr_patient', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const data = await res.json();
                if (data.success && data.patient) {
                    document.getElementById('labPatientName').textContent = data.patient.name || '許瀞文';
                    document.getElementById('labPatientDob').textContent = data.patient.dob || '1989/09/26';
                    document.getElementById('labPatientMrn').textContent = data.patient.mrn || '20260723204122';
                    alert(`✅ OCR 辨識完成！找到病患：${data.patient.name} (${data.patient.dob})`);
                } else {
                    alert("OCR 辨識失敗: " + (data.error || '未知錯誤'));
                }
            } catch (e) {
                console.error("OCR request failed:", e);
                alert("連線失敗。");
            } finally {
                runPatientOcrBtn.disabled = false;
                runPatientOcrBtn.textContent = '🔍 擷取門診畫面 (OCR 病患)';
            }
        });
    }

    if (runSoapCompareBtn) {
        runSoapCompareBtn.addEventListener('click', async () => {
            runSoapCompareBtn.disabled = true;
            runSoapCompareBtn.textContent = '⏳ 推理與 SOAP 生成中...';
            const transcript = document.getElementById('labTranscript').value;
            const patientName = document.getElementById('labPatientName').textContent;
            const patientDob = document.getElementById('labPatientDob').textContent;

            try {
                const res = await fetch('/api/dashboard/soap/compare', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        transcript: transcript,
                        patient_name: patientName,
                        patient_dob: patientDob
                    })
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('cloudSoapResult').value = data.cloud_without_db.soap || '';
                    document.getElementById('localSoapResult').value = data.local_with_db.soap || '';
                } else {
                    alert("SOAP 對比失敗: " + (data.error || '未知錯誤'));
                }
            } catch (e) {
                console.error("SOAP Compare failed:", e);
                alert("連線失敗。");
            } finally {
                runSoapCompareBtn.disabled = false;
                runSoapCompareBtn.textContent = '⚡ 執行雙 LLM SOAP 對比生成';
            }
        });
    }

    if (triggerFactCheckBtn) {
        triggerFactCheckBtn.addEventListener('click', async () => {
            triggerFactCheckBtn.disabled = true;
            triggerFactCheckBtn.textContent = '⏳ 處理中...';
            try {
                const res = await fetch('/api/dashboard/drafts/trigger', { method: 'POST' });
                if (res.ok) {
                    alert("網實核查已啟動！背景正在執行查證、模擬提問與 CRM 分析，請稍候重新載入。");
                } else {
                    alert("啟動失敗，請查看伺服器日誌。");
                }
            } catch (e) {
                console.error("Trigger fact check failed:", e);
                alert("連線失敗。");
            } finally {
                triggerFactCheckBtn.disabled = false;
                triggerFactCheckBtn.textContent = '🔍 執行今日網實核查';
            }
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            window.location.href = '/api/dashboard/export';
        });
    }

    // --- Tab 1: Curation (Batch Workflow) ---
    const logList = document.getElementById('logList');
    const editorPanel = document.getElementById('editorPanel');
    const editorPrompt = document.getElementById('editorPrompt');
    const editorResponse = document.getElementById('editorResponse');
    const saveBtn = document.getElementById('saveBtn');
    const discardBtn = document.getElementById('discardBtn');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const selectHighConfBtn = document.getElementById('selectHighConfBtn');
    const batchSaveBtn = document.getElementById('batchSaveBtn');
    const batchDiscardBtn = document.getElementById('batchDiscardBtn');
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
        const createItem = (data, type, idx, isProactive) => {
            const div = document.createElement('div');
            const key = _getItemKey(type, isProactive ? data.question : (type === 'draft' ? data.original_interaction.messages[0].content : data.timestamp));
            const hasPending = !!pendingEdits[key];
            const isActive = isActiveProactive === isProactive && activeLogIndex === idx;
            
            div.className = `log-item ${isActive ? 'active' : ''} ${hasPending ? 'has-draft' : ''} ${isProactive ? 'proactive-item' : ''}`;
            
            let content = '';
            let meta = '';
            let footer = '';

            if (isProactive) {
                content = data.question;
                meta = `模擬提問`;
                footer = `<span class="badge" style="background:#a855f7;">✨ ${data.service}</span>`;
            } else if (type === 'draft') {
                content = data.original_interaction.messages[0].content;
                meta = `Hermes 建議修正`;
                footer = `<span class="badge" style="background:var(--accent-color);">🔍 待核查</span>`;
            } else {
                content = data.messages[0].content;
                meta = data.timestamp.split('T')[1].split('.')[0];
                footer = `<span class="badge" style="background:#444;">💬 對話紀錄</span>`;
            }

            div.innerHTML = `
                <div style="display:flex; gap:12px; align-items:flex-start;">
                    <input type="checkbox" ${hasPending ? 'checked' : ''} onclick="event.stopPropagation(); toggleItemSelection('${type}', ${idx}, this.checked)">
                    <div style="flex:1;">
                        <div class="log-meta"><span>${meta}</span>${footer}</div>
                        <div class="log-text">${escapeHtml(content)}</div>
                    </div>
                </div>
            `;
            div.onclick = () => isProactive ? selectProactive(idx) : selectLog(idx, type === 'draft');
            return div;
        };

        const draftsToShow = currentDrafts.filter(d => !_getItemKey('draft', d.original_interaction.messages[0].content) in pendingEdits);
        
        proactiveQA.slice().reverse().forEach((p, i) => logList.appendChild(createItem(p, 'proactive', proactiveQA.length - 1 - i, true)));
        currentLogs.slice().reverse().forEach((l, i) => logList.appendChild(createItem(l, 'log', currentLogs.length - 1 - i, false)));
    }

    function _getActiveKey() {
        if (activeLogIndex === -1) return null;
        if (isActiveProactive) return _getItemKey('proactive', proactiveQA[activeLogIndex].question);
        return _getItemKey('log', currentLogs[activeLogIndex].timestamp);
    }

    window.toggleItemSelection = (type, idx, checked) => {
        const item = type === 'proactive' ? proactiveQA[idx] : currentLogs[idx];
        const key = _getItemKey(type, type === 'proactive' ? item.question : item.timestamp);
        if (checked) {
            pendingEdits[key] = {
                prompt: type === 'proactive' ? item.question : item.messages[0].content,
                response: type === 'proactive' ? item.answer : item.messages[1].content,
                index: idx,
                type: type,
                id: type === 'proactive' ? item.question : item.timestamp,
                isProactive: type === 'proactive'
            };
        } else {
            delete pendingEdits[key];
        }
        renderLogs();
    };

    function selectLog(index, hasDraft = false) {
        _updatePendingFromEditor();
        activeLogIndex = index; renderLogs();
        const log = currentLogs[index]; if (!log) return;
        const userMsg = log.messages[0]; const astMsg = log.messages[1];
        const key = _getItemKey(hasDraft ? 'draft' : 'log', hasDraft ? currentDrafts.find(d => d.original_interaction?.messages[0]?.content === userMsg.content)?.timestamp : log.timestamp);
        
        if (pendingEdits[key]) {
            editorPrompt.value = pendingEdits[key].prompt; editorResponse.value = pendingEdits[key].response;
        } else {
            // Field mapping check: userMsg is Q, astMsg is A
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
        
        // Flow Change: Keep the header (🚀 Topic) in the question field
        editorPrompt.value = pendingEdits[key] ? pendingEdits[key].prompt : pqa.question;
        // The answer is already pre-generated by the background LLM during the nightly run
        editorResponse.value = pendingEdits[key] ? pendingEdits[key].response : pqa.answer;
        editorResponse.style.border = '2px solid #a855f7';
        saveBtn.innerHTML = '✅ 批准並存入訓練集';
        if (evidencePanel) evidencePanel.style.display = 'none';
        if (editorPanel) editorPanel.style.display = 'block';
    }

    function _updatePendingFromEditor() {
        if (activeLogIndex === -1) return;
        const key = _getActiveKey();
        const item = pendingEdits[key] || { prompt: editorPrompt.value, response: editorResponse.value, isProactive: isActiveProactive };
        item.prompt = editorPrompt.value;
        item.response = editorResponse.value;
        pendingEdits[key] = item;
    }

    if (saveBtn) saveBtn.addEventListener('click', async () => {
        const key = _getActiveKey();
        if (!key) return;
        _updatePendingFromEditor();
        const item = pendingEdits[key];

        const payload = {
            original_log: item.isProactive ? { messages: [{role:'user', content:item.prompt}] } : currentLogs[item.index],
            corrected_prompt: item.prompt,
            corrected_response: item.response,
            item_type: item.type,
            item_id: item.id
        };

        try {
            const res = await fetch('/api/dashboard/logs/correct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                delete pendingEdits[key];
                activeLogIndex = -1;
                editorPanel.style.display = 'none';
                loadLogs();
            }
        } catch (e) { console.error("Save failed", e); }
    });

    if (batchSaveBtn) batchSaveBtn.addEventListener('click', async () => {
        const keys = Object.keys(pendingEdits);
        if (keys.length === 0) { alert("請先勾選項目。"); return; }
        if (!confirm(`批量儲存 ${keys.length} 筆資料？`)) return;
        
        batchSaveBtn.textContent = '處理中...';
        
        const corrections = keys.map(key => {
            const item = pendingEdits[key];
            return {
                original_log: item.isProactive ? { messages: [{role:'user', content:item.prompt}] } : currentLogs[item.index],
                corrected_prompt: item.prompt,
                corrected_response: item.response,
                item_type: item.type,
                item_id: item.id
            };
        });

        try {
            const res = await fetch('/api/dashboard/logs/batch_correct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ corrections })
            });
            const result = await res.json();
            if (res.ok) {
                alert(`完成！成功: ${result.success_count} 筆。`);
                pendingEdits = {}; 
                activeLogIndex = -1; 
                editorPanel.style.display = 'none';
                loadLogs();
            } else {
                alert(`儲存失敗: ${result.error || '未知錯誤'}`);
            }
        } catch (e) {
            console.error("Batch save failed:", e);
            alert("批量儲存發生錯誤，請查看主控台。");
        } finally {
            batchSaveBtn.textContent = '批量儲存已選';
        }
    });

    if (batchDiscardBtn) batchDiscardBtn.addEventListener('click', async () => {
        const keys = Object.keys(pendingEdits);
        if (keys.length === 0) { alert("請先勾選項目。"); return; }
        if (!confirm(`確定要批量刪除這 ${keys.length} 筆資料嗎？此動作不可撤銷。`)) return;
        
        batchDiscardBtn.disabled = true;
        batchDiscardBtn.textContent = '刪除中...';
        
        const items = keys.map(key => {
            const item = pendingEdits[key];
            return {
                item_type: item.type,
                item_id: item.id
            };
        });

        try {
            const res = await fetch('/api/dashboard/logs/batch_discard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items })
            });
            if (res.ok) {
                const result = await res.json();
                alert(`已刪除 ${result.count} 筆項目。`);
                pendingEdits = {}; 
                activeLogIndex = -1; 
                editorPanel.style.display = 'none';
                loadLogs();
            } else {
                alert("刪除失敗。");
            }
        } catch (e) {
            console.error("Batch discard failed:", e);
            alert("連線失敗。");
        } finally {
            batchDiscardBtn.disabled = false;
            batchDiscardBtn.textContent = '🗑️ 批量刪除已選';
        }
    });

    if (selectHighConfBtn) selectHighConfBtn.addEventListener('click', () => {
        proactiveQA.forEach((p, i) => { if (p.confidence >= 85) toggleItemSelection('proactive', i, true); });
        currentLogs.forEach((l, i) => { if (l.metadata?.confidence_score >= 85) toggleItemSelection('log', i, true); });
    });

    if (selectAllBtn) selectAllBtn.addEventListener('click', () => {
        proactiveQA.forEach((p, i) => toggleItemSelection('proactive', i, true));
        currentLogs.forEach((l, i) => toggleItemSelection('log', i, true));
    });

    function escapeHtml(text) {
        if (!text) return '';
        const map = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#039;"};
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    function truncate(text, length) {
        if (!text || text.length <= length) return text;
        return text.substring(0, length) + '...';
    }

    // --- Tab 4: Article Sync ---
    const articleList = document.getElementById('articleList');
    const articleEditorPanel = document.getElementById('articleEditorPanel');
    const articleTitle = document.getElementById('articleTitle');
    const articleCategory = document.getElementById('articleCategory');
    const articleContent = document.getElementById('articleContent');
    const markSyncedBtn = document.getElementById('markSyncedBtn');
    let currentArticles = [];
    let activeArticleIndex = -1;

    async function loadArticles() {
        if (articleList) articleList.innerHTML = '<div style="padding:20px; color:#666;">載入中...</div>';
        try {
            const res = await fetch('/api/dashboard/articles');
            currentArticles = await res.json();
            renderArticles();
        } catch (e) { console.error("Load articles failed", e); }
    }

    function renderArticles() {
        if (!articleList) return;
        articleList.innerHTML = currentArticles.map((a, i) => `
            <div class="log-item ${activeArticleIndex === i ? 'active' : ''}" onclick="selectArticle(${i})">
                <div class="log-meta"><span>${a.category}</span><span>ID: ${a.id}</span></div>
                <div class="log-text">${escapeHtml(a.title)}</div>
            </div>
        `).join('');
    }

    window.selectArticle = (index) => {
        activeArticleIndex = index; renderArticles();
        const a = currentArticles[index];
        articleTitle.value = a.title; articleCategory.value = a.category; articleContent.value = a.content;
        articleEditorPanel.style.display = 'block';
    };

    if (markSyncedBtn) markSyncedBtn.addEventListener('click', async () => {
        const a = currentArticles[activeArticleIndex];
        try {
            const res = await fetch('/api/dashboard/articles/sync', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: a.id }) });
            if (res.ok) { articleEditorPanel.style.display = 'none'; loadArticles(); }
        } catch (e) { console.error("Sync failed", e); }
    });

    if (document.getElementById('copyTitleBtn')) document.getElementById('copyTitleBtn').addEventListener('click', () => copyToClipboard('articleTitle'));
    if (document.getElementById('copyContentBtn')) document.getElementById('copyContentBtn').addEventListener('click', () => copyToClipboard('articleContent'));

    // --- Tab 5: Analytics ---
    function loadAnalytics() {
        // 1. Load Business Analytics (Procedures & Pain Points)
        fetch('/api/dashboard/analytics').then(r => r.ok ? r.json() : null).then(data => {
            if (!data || !data.procedures) return;
            new Chart(document.getElementById('proceduresChart'), { 
                type: 'bar', 
                data: { 
                    labels: data.procedures.labels, 
                    datasets: [{ label: '詢問次數', data: data.procedures.values, backgroundColor: '#3b82f6' }] 
                }, 
                options: { responsive: true, maintainAspectRatio: false } 
            });
            new Chart(document.getElementById('painPointsChart'), { 
                type: 'pie', 
                data: { 
                    labels: data.pain_points.labels, 
                    datasets: [{ data: data.pain_points.values, backgroundColor: ['#ef4444','#f59e0b','#10b981','#3b82f6','#a855f7'] }] 
                }, 
                options: { responsive: true, maintainAspectRatio: false } 
            });
        });

        // 2. Load System Health Metrics
        fetch('/api/v1/system/metrics').then(r => r.ok ? r.json() : null).then(data => {
            if (!data || !data.health_check || !data.health_check.resources) return;
            const health = data.health_check.resources;
            
            // System Resources Chart
            new Chart(document.getElementById('systemHealthChart'), {
                type: 'doughnut',
                data: {
                    labels: ['CPU 使用率', '記憶體佔用', '硬碟使用率'],
                    datasets: [{
                        data: [health.cpu_percent, health.memory_percent, health.disk_usage],
                        backgroundColor: ['#60a5fa', '#a855f7', '#4ade80'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } }
                }
            });

            // Database Connections Chart
            const db = data.database;
            new Chart(document.getElementById('dbConnChart'), {
                type: 'bar',
                data: {
                    labels: ['目前連線', '剩餘容量', '總連線池'],
                    datasets: [{
                        label: '連線數',
                        data: [db.pool_size - db.available_connections, db.available_connections, db.max_connections],
                        backgroundColor: '#fbbf24'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } } }
                }
            });
        });

        // 3. Load Deep Clinical Insights (ehrapy)
        fetch('/api/dashboard/clinical_insights').then(r => r.ok ? r.json() : null).then(data => {
            if (!data) return;
            
            // Clinical Clusters (Using Age Distribution for this view)
            new Chart(document.getElementById('clinicalClustersChart'), {
                type: 'bar',
                data: {
                    labels: data.age_distribution.labels,
                    datasets: [{
                        label: '病患年齡分佈',
                        data: data.age_distribution.values,
                        backgroundColor: '#10b981',
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } } }
                }
            });
            
            // ICD-10 Risk Analysis
            if (data.icd10_risks && data.icd10_risks.labels.length > 0) {
                new Chart(document.getElementById('icd10RiskChart'), {
                    type: 'bar',
                    data: {
                        labels: data.icd10_risks.labels,
                        datasets: [{
                            label: '高風險病患數',
                            data: data.icd10_risks.values,
                            backgroundColor: '#ef4444',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { stepSize: 1 } } }
                    }
                });
                
                // Render Knowledge Cards
                const knowledgeList = document.getElementById('icd10KnowledgeList');
                if (knowledgeList && data.icd10_risks.knowledge) {
                    let html = '';
                    for (const [key, info] of Object.entries(data.icd10_risks.knowledge)) {
                        if (info && info.name) {
                            html += `
                                <div style="background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 8px; border-left: 4px solid #ef4444;">
                                    <h4 style="margin: 0 0 10px 0; color: #f87171;">${key} - ${info.name}</h4>
                                    <div style="font-size: 0.85rem; color: #cbd5e1;">
                                        ${info.drugs.length > 0 ? `<p style="margin: 4px 0;"><strong>💊 推薦用藥:</strong> ${info.drugs.join(', ')}</p>` : ''}
                                        ${info.checks.length > 0 ? `<p style="margin: 4px 0;"><strong>🩺 建議檢查:</strong> ${info.checks.join(', ')}</p>` : ''}
                                        ${info.do_eat.length > 0 ? `<p style="margin: 4px 0;"><strong>✅ 建議飲食:</strong> ${info.do_eat.join(', ')}</p>` : ''}
                                        ${info.not_eat.length > 0 ? `<p style="margin: 4px 0;"><strong>❌ 飲食禁忌:</strong> ${info.not_eat.join(', ')}</p>` : ''}
                                    </div>
                                </div>
                            `;
                        }
                    }
                    knowledgeList.innerHTML = html;
                }
            }

            // Knowledge Gaps List
            const gapList = document.getElementById('knowledgeGapsList');
            if (gapList && data.knowledge_gaps) {
                if (data.knowledge_gaps.length === 0) {
                    gapList.innerHTML = '<div class="alert alert-success" style="font-size:0.85rem;">✅ 目前 RAG 信心度表現良好，無明顯知識缺口。</div>';
                } else {
                    gapList.innerHTML = `
                        <div style="font-size:0.85rem; color:#94a3b8; margin-bottom:10px;">偵測到以下主題 AI 信心度較低，建議補充 PageIndex：</div>
                        ${data.knowledge_gaps.map(g => `
                            <div style="display:flex; justify-content:between; align-items:center; margin-bottom:8px; background:rgba(0,0,0,0.2); padding:10px; border-radius:8px;">
                                <div style="flex:1;">
                                    <span style="color:#f87171; font-weight:600;"># ${g.topic}</span>
                                    <div style="font-size:0.7rem; color:#64748b;">出現頻率: ${g.count} 次</div>
                                </div>
                                <button class="btn btn-sm" style="background:var(--accent-color); color:white; font-size:0.7rem;" onclick="alert('請前往上傳資料頁籤，補充此主題的詳細文件。')">補強知識</button>
                            </div>
                        `).join('')}
                    `;
                }
            }
        });

        // 4. Load B2B Outreach ROI Analytics
        fetch('/api/dashboard/analytics/b2b').then(r => r.ok ? r.json() : null).then(res => {
            if (!res || !res.success || !res.data) return;
            const b2b = res.data;
            const leadsEl = document.getElementById('b2bTotalLeads');
            const sentEl = document.getElementById('b2bTotalSent');
            const linkedEl = document.getElementById('b2bTotalLinked');
            const topListEl = document.getElementById('b2bTopLeadsList');

            if (leadsEl) leadsEl.textContent = b2b.total_leads;
            if (sentEl) sentEl.textContent = b2b.total_emails_sent;
            if (linkedEl) linkedEl.textContent = b2b.total_line_linked;

            if (topListEl && b2b.top_leads) {
                topListEl.innerHTML = b2b.top_leads.map(lead => {
                    let channelBadge = '<span style="font-size:0.75rem; padding:2px 6px; border-radius:4px; background:rgba(96,165,250,0.2); color:#60a5fa;">📧 Email</span>';
                    if (lead.outreach_channel === 'messenger') {
                        channelBadge = '<span style="font-size:0.75rem; padding:2px 6px; border-radius:4px; background:rgba(167,139,246,0.2); color:#a78bfa;">💬 Messenger</span>';
                    } else if (lead.outreach_channel === 'post_comment') {
                        channelBadge = '<span style="font-size:0.75rem; padding:2px 6px; border-radius:4px; background:rgba(251,146,60,0.2); color:#fb923c;">💬 Comment</span>';
                    }
                    const categoryTag = `<span style="font-size:0.7rem; color:#94a3b8; margin-left:6px;">[${lead.category || 'General'}]</span>`;

                    return `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <div>
                                🏢 <strong>${lead.company_name}</strong> (${lead.company_id}) ${categoryTag}
                                <div style="margin-top:4px;">${channelBadge}</div>
                            </div>
                            <div style="display:flex; gap:12px; align-items:center;">
                                <div>發送數: <span style="color:#a78bfa; font-weight:bold;">${lead.emails_sent}</span> | VIP 綁定: <span style="color:#34d399; font-weight:bold;">${lead.line_linked_count}</span></div>
                                <button class="tab-btn" style="font-size:0.75rem; padding:4px 8px; background:rgba(167,139,246,0.15); border:1px solid rgba(167,139,246,0.3); color:#a78bfa;" onclick="sendB2bEmail('${lead.company_id}')">📨 觸發開拓發送</button>
                            </div>
                        </div>
                    `;
                }).join('');
            }
        });

        // 10km Scrape Button Handler
        const scrapeBtn = document.getElementById('trigger10kmScrapeBtn');
        if (scrapeBtn && !scrapeBtn.dataset.bound) {
            scrapeBtn.dataset.bound = "true";
            scrapeBtn.addEventListener('click', async () => {
                const msgEl = document.getElementById('b2bAddSuccessMsg');
                try {
                    const res = await fetch('/api/dashboard/analytics/b2b/scrape_10km', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ category: 'Local_FB_Public', limit: 3 })
                    });
                    const data = await res.json();
                    if (data.success) {
                        if (msgEl) {
                            msgEl.style.display = 'block';
                            msgEl.innerHTML = `🕷️ 成功抓取洗入 ${data.count} 家 10km 在地店家與個人公開 Facebook 目標！`;
                        }
                        loadAnalytics();
                    } else {
                        alert('爬取失敗: ' + (data.error || '未知錯誤'));
                    }
                } catch (e) {
                    alert('爬取失敗: ' + e.message);
                }
            });
        }

        // Add B2B Lead Button Handler
        const addBtn = document.getElementById('addB2bLeadBtn');
        if (addBtn && !addBtn.dataset.bound) {
            addBtn.dataset.bound = "true";
            addBtn.addEventListener('click', async () => {
                const name = document.getElementById('newB2bName').value.trim();
                const id = document.getElementById('newB2bId').value.trim();
                const email = document.getElementById('newB2bEmail').value.trim();
                const msgEl = document.getElementById('b2bAddSuccessMsg');

                if (!name || !id) {
                    alert('請輸入企業名稱與企業代號！');
                    return;
                }

                try {
                    const res = await fetch('/api/dashboard/analytics/b2b/add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ company_name: name, company_id: id, contact_email: email })
                    });
                    const data = await res.json();
                    if (data.success) {
                        if (msgEl) {
                            msgEl.style.display = 'block';
                            msgEl.innerHTML = `✅ 成功建立特約目標！UTM Token: <strong>${data.utm_token}</strong>`;
                        }
                        document.getElementById('newB2bName').value = '';
                        document.getElementById('newB2bId').value = '';
                        document.getElementById('newB2bEmail').value = '';
                        loadAnalytics();
                    } else {
                        alert('建立失敗: ' + (data.error || '未知錯誤'));
                    }
                } catch (e) {
                    alert('建立失敗: ' + e.message);
                }
            });
        }
    }

    // --- Tab 2: Upload ---
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const folderInput = document.getElementById('folderInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadProgressContainer = document.getElementById('uploadProgressContainer');
    const uploadProgressBar = document.getElementById('uploadProgressBar');
    if (document.getElementById('btnSelectFiles')) document.getElementById('btnSelectFiles').addEventListener('click', () => fileInput.click());
    if (document.getElementById('btnSelectFolder')) document.getElementById('btnSelectFolder').addEventListener('click', () => folderInput.click());
    if (dropzone) {
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => { e.preventDefault(); dropzone.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
    }
    if (fileInput) fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
    if (folderInput) folderInput.addEventListener('change', (e) => handleFiles(e.target.files));
    async function handleFiles(files) {
        if (!files.length) return;
        const type = document.getElementById('dataTypeSelect').value;
        uploadStatus.textContent = `準備上傳 ${files.length} 個檔案...`;
        uploadProgressContainer.style.display = 'block';
        let successCount = 0; let failCount = 0;
        for (let i = 0; i < files.length; i++) {
            const formData = new FormData(); formData.append('file', files[i]); formData.append('type', type);
            try {
                const res = await fetch('/api/dashboard/upload', { method: 'POST', body: formData });
                if (res.ok) successCount++; else failCount++;
                const p = Math.round(((i + 1) / files.length) * 100); uploadProgressBar.style.width = p + '%';
            } catch (e) { failCount++; }
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
        const div = document.createElement('div'); div.className = `message bot-msg`;
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

    const aiRefineBtn = document.getElementById('aiRefineBtn');

    if (aiRefineBtn) {
        aiRefineBtn.addEventListener('click', async () => {
            const originalText = aiRefineBtn.innerHTML;
            aiRefineBtn.disabled = true;
            aiRefineBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 思考中...';
            
            try {
                // Get route from active log metadata if possible
                let route = 'general';
                if (activeLogIndex !== -1 && !isActiveProactive) {
                    route = currentLogs[activeLogIndex].metadata?.route_used || 'special';
                }

                const response = await fetch('/api/v1/curation/suggest_correction', {
                    method: 'POST',
                    headers: { 
                        'X-Staff-ID': 'staff-001',
                        'Content-Type': 'application/json' 
                    },
                    body: JSON.stringify({
                        prompt: editorPrompt.value,
                        current_answer: editorResponse.value,
                        route: route
                    })
                });
                const result = await response.json();
                if (result.success) {
                    editorResponse.value = result.suggestion;
                    // Update pending edits if the item is selected
                    const key = _getActiveKey();
                    if (key && pendingEdits[key]) {
                        pendingEdits[key].response = result.suggestion;
                    }
                    console.log("AI suggestion applied.");
                } else {
                    alert("AI 建議獲取失敗: " + result.error);
                }
            } catch (e) { 
                console.error("AI suggestion error:", e);
                alert("連線失敗，請檢查後端服務。"); 
            } finally {
                aiRefineBtn.disabled = false;
                aiRefineBtn.innerHTML = originalText;
            }
        });
    }

        // --- SOAP Lab Copy & Clear Handlers ---
        const labTranscript = document.getElementById('labTranscript');
        const clearTranscriptBtn = document.getElementById('clearTranscriptBtn');
        const copyTranscriptBtn = document.getElementById('copyTranscriptBtn');
        const copyCloudSoapBtn = document.getElementById('copyCloudSoapBtn');
        const copyLocalSoapBtn = document.getElementById('copyLocalSoapBtn');
        const clearPatientInfoBtn = document.getElementById('clearPatientInfoBtn');

        const quickPatientSelect = document.getElementById('quickPatientSelect');
        if (quickPatientSelect) {
            quickPatientSelect.addEventListener('change', (e) => {
                const parts = e.target.value.split('|');
                if (parts.length >= 3) {
                    const labPatientName = document.getElementById('labPatientName');
                    const labPatientDob = document.getElementById('labPatientDob');
                    const labPatientMrn = document.getElementById('labPatientMrn');
                    if (labPatientName) labPatientName.innerText = parts[0];
                    if (labPatientDob) labPatientDob.innerText = parts[1];
                    if (labPatientMrn) labPatientMrn.innerText = parts[2];
                }
            });
        }

        if (clearPatientInfoBtn) {
            clearPatientInfoBtn.addEventListener('click', () => {
                const labPatientName = document.getElementById('labPatientName');
                const labPatientDob = document.getElementById('labPatientDob');
                const labPatientMrn = document.getElementById('labPatientMrn');
                if (labPatientName) labPatientName.innerText = '未辨識';
                if (labPatientDob) labPatientDob.innerText = '--/--/--';
                if (labPatientMrn) labPatientMrn.innerText = 'N/A';
            });
        }

        if (clearTranscriptBtn) {
            clearTranscriptBtn.addEventListener('click', () => {
                if (labTranscript) {
                    labTranscript.value = '';
                    labTranscript.focus();
                }
            });
        }

        const copyTextToClipboard = async (text, btnElement, defaultLabel, isSoapOnly = false) => {
            if (!text) return;
            let textToCopy = text;
            if (isSoapOnly) {
                // 剔除病患姓名、生日、日期、耗時與分隔線，僅保留精準 S / O / A / P 的純病歷紀錄
                textToCopy = textToCopy.replace(/^\*\*病患姓名[^\n]*\n?/gm, '')
                                       .replace(/^\*\*出生年月日[^\n]*\n?/gm, '')
                                       .replace(/^\*\*診察日期[^\n]*\n?/gm, '')
                                       .replace(/^⏱️[^\n]*\n?/gm, '')
                                       .replace(/^---[^\n]*\n?/gm, '')
                                       .trim();
            }
            try {
                await navigator.clipboard.writeText(textToCopy);
                if (btnElement) {
                    btnElement.innerText = '✅ 已複製純 SOAP！';
                    setTimeout(() => { btnElement.innerText = defaultLabel; }, 2000);
                }
            } catch (err) {
                console.error('Clipboard copy failed:', err);
            }
        };

        if (copyTranscriptBtn) {
            copyTranscriptBtn.addEventListener('click', () => {
                copyTextToClipboard(labTranscript ? labTranscript.value : '', copyTranscriptBtn, '📋 複製');
            });
        }

        if (copyCloudSoapBtn) {
            copyCloudSoapBtn.addEventListener('click', () => {
                const cloudSoapResult = document.getElementById('cloudSoapResult');
                copyTextToClipboard(cloudSoapResult ? cloudSoapResult.value : '', copyCloudSoapBtn, '📋 複製 SOAP', true);
            });
        }

        if (copyLocalSoapBtn) {
            copyLocalSoapBtn.addEventListener('click', () => {
                const localSoapResult = document.getElementById('localSoapResult');
                copyTextToClipboard(localSoapResult ? localSoapResult.value : '', copyLocalSoapBtn, '📋 複製 SOAP', true);
            });
        }

    // --- Knowledge Map (D3.js) ---
    const knowledgeGraphContainer = document.getElementById('knowledgeGraph');
    const graphTooltip = document.getElementById('graphTooltip');

    async function loadKnowledgeGraph() {
        if (!knowledgeGraphContainer) return;
        console.log("Loading Knowledge Graph data...");
        try {
            // Add cache buster
            const res = await fetch('/api/dashboard/knowledge_graph?cb=' + new Date().getTime());
            if (!res.ok) throw new Error("HTTP " + res.status);
            const data = await res.json();
            console.log("Graph data received:", data.nodes.length, "nodes");
            renderD3Graph(data);
        } catch (e) {
            console.error("Failed to load knowledge graph:", e);
            knowledgeGraphContainer.innerHTML = `<div style="color:#f87171; padding:20px;">⚠️ 載入失敗: ${e.message}</div>`;
        }
    }

    function renderD3Graph(data) {
        if (!knowledgeGraphContainer) return;
        knowledgeGraphContainer.innerHTML = '';
        
        if (!data || !data.nodes || data.nodes.length === 0) {
            knowledgeGraphContainer.innerHTML = '<div style="display:flex; align-items:center; justify-content:center; height:100%; color:#64748b;">⏳ 推理樹建置中，請稍候重整... (PageIndex 2.0 仍在轉換舊文件)</div>';
            return;
        }

        const width = knowledgeGraphContainer.clientWidth || 800;
        const height = knowledgeGraphContainer.clientHeight || 600;

        const svg = d3.select("#knowledgeGraph")
            .append("svg")
            .attr("width", "100%")
            .attr("height", "100%")
            .attr("viewBox", [0, 0, width, height]);

        const g = svg.append("g");

        svg.call(d3.zoom().scaleExtent([0.1, 8]).on("zoom", (event) => g.attr("transform", event.transform)));

        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(220))
            .force("charge", d3.forceManyBody().strength(-700))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(90));

        const link = g.append("g")
            .selectAll("line")
            .data(data.links)
            .join("line")
            .attr("stroke", "rgba(56, 189, 248, 0.35)")
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", d => d.type === 'has_correction' ? "5,5" : "0");

        const node = g.append("g")
            .selectAll("g")
            .data(data.nodes)
            .join("g")
            .style("cursor", "pointer")
            .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));

        node.append("circle")
            .attr("r", d => d.type === 'physician_note' ? 14 : 20)
            .attr("fill", d => d.type === 'physician_note' ? "#fbbf24" : (d.category === 'special' ? "#38bdf8" : "#10b981"))
            .attr("stroke", "rgba(255,255,255,0.4)")
            .attr("stroke-width", 2.5);

        node.append("text")
            .text(d => d.id)
            .attr("x", 26)
            .attr("y", 6)
            .attr("fill", "#f8fafc")
            .style("font-size", "0.95rem")
            .style("font-weight", "600");

        node.on("mouseover", (event, d) => {
            graphTooltip.style.display = 'block';
            graphTooltip.innerHTML = `<div style="font-weight:600;">${d.id}</div><div style="font-size:0.7rem; color:#94a3b8;">${d.type === 'physician_note' ? '醫師校正筆記' : '醫療主題'}</div>`;
        }).on("mousemove", (event) => {
            graphTooltip.style.left = (event.pageX + 20) + 'px';
            graphTooltip.style.top = (event.pageY - 20) + 'px';
        }).on("mouseout", () => {
            graphTooltip.style.display = 'none';
        });

        simulation.on("tick", () => {
            link.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });

        function dragstarted(event) { if (!event.active) simulation.alphaTarget(0.3).restart(); event.subject.fx = event.subject.x; event.subject.fy = event.subject.y; }
        function dragged(event) { event.subject.fx = event.x; event.subject.fy = event.y; }
        function dragended(event) { if (!event.active) simulation.alphaTarget(0); event.subject.fx = null; event.subject.fy = null; }
    }

    loadLogs();
});
