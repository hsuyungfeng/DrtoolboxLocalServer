document.addEventListener('DOMContentLoaded', () => {
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
                    <span>Route: ${log.metadata.route_used}</span>
                </div>
                <div class="log-prompt">${userMsg ? userMsg.content : 'No prompt'}</div>
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
        
        saveBtn.textContent = 'Saving...';
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
                saveBtn.textContent = 'Saved!';
                setTimeout(() => saveBtn.textContent = 'Verify & Save Pair', 2000);
            } else {
                alert('Failed to save correction.');
                saveBtn.textContent = 'Verify & Save Pair';
            }
        } catch (e) {
            console.error(e);
            saveBtn.textContent = 'Verify & Save Pair';
        }
    });

    exportBtn.addEventListener('click', () => {
        window.location.href = '/api/dashboard/export';
    });

    loadLogs();
});
