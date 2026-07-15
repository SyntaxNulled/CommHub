// CommHub Frontend — Alpine.js + vanilla JS
document.addEventListener('alpine:init', () => {
    Alpine.data('app', () => ({
        // State
        page: 'inbox',
        health: null,
        accounts: [],
        emails: [],
        selectedEmail: null,
        loading: true,
        error: null,

        // Sidebar
        sidebarLinks: [
            { id: 'inbox', label: 'Inbox', icon: '📥' },
            { id: 'sent', label: 'Sent', icon: '📤' },
            { id: 'drafts', label: 'Drafts', icon: '📝' },
            { id: 'starred', label: 'Starred', icon: '⭐' },
            { id: 'calendar', label: 'Calendar', icon: '📅' },
            { id: 'settings', label: 'Settings', icon: '⚙️' },
        ],

        async init() {
            await this.checkHealth();
            this.loading = false;
        },

        async checkHealth() {
            try {
                const res = await fetch('/api/health');
                this.health = await res.json();
            } catch (e) {
                this.error = 'Failed to connect to backend';
            }
        },

        navigate(pageId) {
            this.page = pageId;
            this.selectedEmail = null;
        },

        formatDate(dateStr) {
            if (!dateStr) return '';
            const d = new Date(dateStr);
            const now = new Date();
            if (d.toDateString() === now.toDateString()) {
                return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
    }));
});
