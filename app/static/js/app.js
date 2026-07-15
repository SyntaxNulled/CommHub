// CommHub Frontend — Alpine.js + vanilla JS
document.addEventListener('alpine:init', () => {
    Alpine.data('app', () => ({
        // Navigation
        page: 'inbox',
        health: null,
        accounts: [],
        emails: [],
        selectedEmail: null,
        loading: true,
        error: null,

        sidebarLinks: [
            { id: 'inbox', label: 'Inbox', icon: '📥' },
            { id: 'sent', label: 'Sent', icon: '📤' },
            { id: 'drafts', label: 'Drafts', icon: '📝' },
            { id: 'starred', label: 'Starred', icon: '⭐' },
            { id: 'calendar', label: 'Calendar', icon: '📅' },
            { id: 'settings', label: 'Settings', icon: '⚙️' },
        ],

        // AI State
        aiPanelOpen: false,
        aiInput: '',
        aiTone: 'professional',
        aiLoading: false,
        aiResult: '',
        aiResultProvider: '',
        aiError: '',
        aiToneSelector: false,

        // AI Config
        aiConfigs: [],
        availableProviders: [],
        aiFormOpen: false,
        aiFormEdit: false,
        aiForm: {
            provider_type: '',
            display_name: '',
            api_key: '',
            base_url: '',
            model: '',
            temperature: 0.7,
            max_tokens: 1024,
        },

        // Computed
        get unconfiguredProviders() {
            const configured = this.aiConfigs.map(c => c.provider_type);
            return this.availableProviders.filter(p => !configured.includes(p));
        },
        get aiActiveLabel() {
            const active = this.aiConfigs.find(c => c.is_active);
            return active ? active.display_name : null;
        },

        // --- Init ---
        async init() {
            await this.checkHealth();
            await this.loadAiProviders();
            await this.loadAiConfigs();
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
            if (pageId !== 'settings') this.closeAiForm();
        },

        // --- AI Providers CRUD ---
        async loadAiProviders() {
            try {
                const res = await fetch('/api/ai/providers');
                if (res.ok) this.availableProviders = await res.json();
            } catch (e) {}
        },

        async loadAiConfigs() {
            try {
                const res = await fetch('/api/ai/configs');
                if (res.ok) this.aiConfigs = await res.json();
            } catch (e) {}
        },

        openNewAiConfig(providerType) {
            this.aiForm = {
                provider_type: providerType,
                display_name: providerType.charAt(0).toUpperCase() + providerType.slice(1),
                api_key: '',
                base_url: providerType === 'ollama' ? 'http://localhost:11434' : '',
                model: '',
                temperature: 0.7,
                max_tokens: 1024,
            };
            this.aiFormEdit = false;
            this.aiFormOpen = true;
        },

        editAiConfig(cfg) {
            this.aiForm = {
                provider_type: cfg.provider_type,
                display_name: cfg.display_name,
                api_key: cfg.api_key,
                base_url: cfg.base_url || '',
                model: cfg.model,
                temperature: cfg.temperature,
                max_tokens: cfg.max_tokens,
            };
            this.aiFormEdit = true;
            this.aiFormOpen = true;
        },

        closeAiForm() {
            this.aiFormOpen = false;
            this.aiFormEdit = false;
        },

        async saveAiConfig() {
            this.aiError = '';
            try {
                const url = this.aiFormEdit
                    ? `/api/ai/configs/${this.aiForm.provider_type}`
                    : '/api/ai/configs';
                const method = this.aiFormEdit ? 'PUT' : 'POST';
                const res = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.aiForm),
                });
                if (!res.ok) {
                    const err = await res.json();
                    this.aiError = err.detail || 'Failed to save';
                    return;
                }
                this.closeAiForm();
                await this.loadAiConfigs();
            } catch (e) {
                this.aiError = 'Network error saving config';
            }
        },

        async activateAiProvider(providerType) {
            try {
                const res = await fetch(`/api/ai/configs/${providerType}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_active: true }),
                });
                if (res.ok) await this.loadAiConfigs();
            } catch (e) {}
        },

        async deleteAiConfig(providerType) {
            try {
                const res = await fetch(`/api/ai/configs/${providerType}`, { method: 'DELETE' });
                if (res.ok) await this.loadAiConfigs();
            } catch (e) {}
        },

        // --- AI Actions ---
        async aiAction(action) {
            if (!this.aiInput.trim()) return;
            this.aiLoading = true;
            this.aiResult = '';
            this.aiError = '';
            this.aiToneSelector = action === 'draft';

            try {
                let res;
                if (action === 'draft') {
                    res = await fetch('/api/ai/draft', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email_text: this.aiInput, tone: this.aiTone }),
                    });
                } else if (action === 'summarize') {
                    res = await fetch('/api/ai/summarize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email_text: this.aiInput }),
                    });
                } else if (action === 'categorize') {
                    res = await fetch('/api/ai/categorize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ subject: '', body: this.aiInput }),
                    });
                } else if (action === 'chat') {
                    res = await fetch('/api/ai/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: this.aiInput }),
                    });
                }

                if (res && res.ok) {
                    const data = await res.json();
                    this.aiResult = data.result;
                    this.aiResultProvider = `${data.provider} (${data.model})`;
                } else if (res) {
                    const err = await res.json();
                    this.aiError = err.detail || 'AI request failed';
                }
            } catch (e) {
                this.aiError = 'Network error during AI request';
            } finally {
                this.aiLoading = false;
            }
        },

        copyAiResult() {
            navigator.clipboard?.writeText(this.aiResult);
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
