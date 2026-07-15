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
            { id: 'automation', label: 'Automation', icon: '⚡' },
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
            await this.loadTriggerTypes();
            await this.loadActionTypes();
            await this.loadAutomationRules();
            await this.loadScheduledJobs();
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
            if (pageId !== 'automation') this.closeRuleForm();
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

        // --- Automation State ---
        automationRules: [],
        triggerTypes: [],
        actionTypes: [],
        scheduledJobs: [],
        ruleFormOpen: false,
        ruleFormEdit: false,
        ruleForm: {
            name: '', description: '', trigger_type: 'new_email',
            trigger_config: {}, action_type: 'auto_reply',
            action_config: {}, cron_schedule: '', is_enabled: true, account_id: null,
        },

        async loadAutomationRules() {
            try {
                const res = await fetch('/api/automation/rules');
                if (res.ok) this.automationRules = await res.json();
            } catch (e) {}
        },

        async loadTriggerTypes() {
            try {
                const res = await fetch('/api/automation/trigger-types');
                if (res.ok) this.triggerTypes = await res.json();
            } catch (e) {}
        },

        async loadActionTypes() {
            try {
                const res = await fetch('/api/automation/action-types');
                if (res.ok) this.actionTypes = await res.json();
            } catch (e) {}
        },

        async loadScheduledJobs() {
            try {
                const res = await fetch('/api/automation/scheduler/jobs');
                if (res.ok) this.scheduledJobs = await res.json();
            } catch (e) {}
        },

        openNewRule() {
            this.ruleForm = {
                name: '', description: '', trigger_type: 'new_email',
                trigger_config: {}, action_type: 'auto_reply',
                action_config: {}, cron_schedule: '', is_enabled: true, account_id: null,
            };
            this.ruleFormEdit = false;
            this.ruleFormOpen = true;
        },

        editRule(rule) {
            this.ruleForm = {
                name: rule.name, description: rule.description || '',
                trigger_type: rule.trigger_type, trigger_config: rule.trigger_config || {},
                action_type: rule.action_type, action_config: rule.action_config || {},
                cron_schedule: rule.cron_schedule || '', is_enabled: rule.is_enabled,
                account_id: rule.account_id,
            };
            this.ruleFormEdit = true;
            this.ruleFormEditId = rule.id;
            this.ruleFormOpen = true;
        },

        closeRuleForm() {
            this.ruleFormOpen = false;
            this.ruleFormEdit = false;
            this.ruleFormEditId = null;
        },

        async saveRule() {
            try {
                const payload = { ...this.ruleForm };
                if (!payload.cron_schedule) payload.cron_schedule = null;
                const url = this.ruleFormEdit
                    ? `/api/automation/rules/${this.ruleFormEditId}`
                    : '/api/automation/rules';
                const method = this.ruleFormEdit ? 'PUT' : 'POST';
                const res = await fetch(url, {
                    method, headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (res.ok) {
                    this.closeRuleForm();
                    await this.loadAutomationRules();
                    await this.loadScheduledJobs();
                }
            } catch (e) {}
        },

        async deleteRule(ruleId) {
            try {
                const res = await fetch(`/api/automation/rules/${ruleId}`, { method: 'DELETE' });
                if (res.ok) {
                    await this.loadAutomationRules();
                    await this.loadScheduledJobs();
                }
            } catch (e) {}
        },

        async toggleRule(ruleId) {
            try {
                const res = await fetch(`/api/automation/rules/${ruleId}/toggle`, { method: 'POST' });
                if (res.ok) {
                    await this.loadAutomationRules();
                    await this.loadScheduledJobs();
                }
            } catch (e) {}
        },

        triggerTypeLabel(type) {
            const labels = { new_email: '📩 New Email', keyword_match: '🔑 Keyword Match', cron_schedule: '⏰ Cron Schedule' };
            return labels[type] || type;
        },

        actionTypeLabel(type) {
            const labels = { auto_reply: '✉️ Auto-Reply', categorize: '🏷️ Categorize', mark_read: '✔️ Mark Read', star: '⭐ Star', forward: '📤 Forward' };
            return labels[type] || type;
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
