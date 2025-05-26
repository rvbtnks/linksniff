// static/script.js
// Version: updated for new UI layout

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const menuToggle           = document.getElementById('menu-toggle');
    const sidebar              = document.getElementById('sidebar');
    const closeMenuBtn         = document.querySelector('.close-menu-btn');
    const urlInput             = document.getElementById('url-input');
    const addButton            = document.getElementById('add-button');
    const refreshButton        = document.getElementById('refresh-button');
    const clearCompletedButton = document.getElementById('clear-completed-button');
    const clearAllButton       = document.getElementById('clear-all-button');
    const queueList            = document.getElementById('queue-list');
    const themeToggle          = document.getElementById('theme-toggle');
    const concurrencyInput     = document.getElementById('concurrency');
    const updateYtdlpButton    = document.getElementById('update-ytdlp-button');
    
    // Sidebar toggle
    menuToggle.addEventListener('click', () => {
        sidebar.classList.add('open');
    });
    
    closeMenuBtn.addEventListener('click', () => {
        sidebar.classList.remove('open');
    });
    
    // Click outside sidebar to close
    document.addEventListener('click', (e) => {
        if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });
    
    // Persist theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.classList.toggle('dark', savedTheme === 'dark');
    themeToggle.checked = (savedTheme === 'dark');
    themeToggle.addEventListener('change', () => {
        const isDark = themeToggle.checked;
        document.body.classList.toggle('dark', isDark);
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });

    // Fetch & set initial concurrency and queue
    async function loadSettings() {
        try {
            const response = await fetch('/jobs');
            const data = await response.json();
            concurrencyInput.value = data.concurrency;
            renderQueue(data.jobs);
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }
    
    concurrencyInput.addEventListener('change', () => {
        fetch('/set_concurrency', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({concurrency: concurrencyInput.value})
        });
    });

    // Update yt-dlp
    updateYtdlpButton.addEventListener('click', async function() {
        const originalText = updateYtdlpButton.textContent;
        updateYtdlpButton.textContent = 'Updating...';
        updateYtdlpButton.disabled = true;
        
        try {
            const response = await fetch('/update_ytdlp', {method: 'POST'});
            const result = await response.json();
            
            if (result.success) {
                updateYtdlpButton.textContent = 'Updated!';
                setTimeout(() => {
                    updateYtdlpButton.textContent = originalText;
                }, 2000);
            } else {
                updateYtdlpButton.textContent = 'Failed';
                console.error('yt-dlp update failed:', result.error);
                setTimeout(() => {
                    updateYtdlpButton.textContent = originalText;
                }, 2000);
            }
        } catch (error) {
            updateYtdlpButton.textContent = 'Error';
            console.error('Error updating yt-dlp:', error);
            setTimeout(() => {
                updateYtdlpButton.textContent = originalText;
            }, 2000);
        } finally {
            updateYtdlpButton.disabled = false;
        }
    });

    // Add URLs (one per line)
    addButton.addEventListener('click', async function() {
        const raw = urlInput.value;
        const urls = raw
            .split(/\r?\n/)
            .map(u => u.trim())
            .filter(u => u.length > 0);
        
        if (urls.length === 0) {
            alert('Please enter at least one URL');
            return;
        }
        
        // Set loading state
        const originalText = addButton.textContent;
        addButton.textContent = 'Adding...';
        addButton.disabled = true;
        
        try {
            for (const url of urls) {
                const res = await fetch('/add', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({url})
                });
                if (!res.ok) {
                    const error = await res.json();
                    alert(error.error);
                }
            }
            urlInput.value = '';
            loadSettings();
        } finally {
            // Reset button state
            addButton.textContent = originalText;
            addButton.disabled = false;
        }
    });

    // Clear completed only
    clearCompletedButton.addEventListener('click', async function() {
        const originalText = clearCompletedButton.textContent;
        clearCompletedButton.textContent = 'Clearing...';
        clearCompletedButton.disabled = true;
        
        try {
            await fetch('/clear_completed', {method: 'POST'});
            loadSettings();
        } finally {
            clearCompletedButton.textContent = originalText;
            clearCompletedButton.disabled = false;
        }
    });

    // Clear all (including failed)
    clearAllButton.addEventListener('click', async function() {
        if (!confirm('Are you sure you want to clear *all* tasks?')) return;
        
        const originalText = clearAllButton.textContent;
        clearAllButton.textContent = 'Clearing...';
        clearAllButton.disabled = true;
        
        try {
            await fetch('/clear_all', {method: 'POST'});
            loadSettings();
        } finally {
            clearAllButton.textContent = originalText;
            clearAllButton.disabled = false;
        }
    });

    // Render queue
    function renderQueue(jobs) {
        queueList.innerHTML = '';
        jobs.forEach(job => {
            const li = document.createElement('li');
            li.className = 'queue-item';
            if (job.status === 'failed') {
                li.classList.add('failed');
            }
            
            li.innerHTML = `
                <div class="status-indicator status-${job.status}"></div>
                <div class="queue-content">
                    <div class="queue-url">[${job.script}] ${job.url}</div>
                    <div class="queue-meta">#${job.id} • ${job.status} • ${job.added}</div>
                </div>
            `;
            
            // Failed → clickable to requeue
            if (job.status === 'failed') {
                li.style.cursor = 'pointer';
                li.title = 'Click to re-queue';
                li.addEventListener('click', async () => {
                    // Disable clicking during requeue
                    li.style.pointerEvents = 'none';
                    li.style.opacity = '0.6';
                    const originalTitle = li.title;
                    li.title = 'Re-queueing...';
                    
                    try {
                        await fetch(`/requeue/${job.id}`, {method:'POST'});
                        loadSettings();
                    } finally {
                        li.style.pointerEvents = '';
                        li.style.opacity = '';
                        li.title = originalTitle;
                    }
                });
            }
            queueList.appendChild(li);
        });
    }

    // Manual refresh
    refreshButton.addEventListener('click', async function() {
        const originalText = refreshButton.textContent;
        refreshButton.textContent = 'Refreshing...';
        refreshButton.disabled = true;
        
        try {
            await loadSettings();
        } finally {
            refreshButton.textContent = originalText;
            refreshButton.disabled = false;
        }
    });

    // Auto-refresh every 5s
    setInterval(loadSettings, 5000);
    loadSettings();
});