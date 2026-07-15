// CommHub Frontend — Alpine.js + vanilla JS
document.addEventListener('alpine:init', () => {
    Alpine.data('app', () => ({
        // Navigation
        page: 'inbox',
        health: null,
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

        // --- Email State ---
        accounts: [],
        emails: [],
        selectedEmail: null,
        currentFolder: 'INBOX',
        composeOpen: false,
        composeForm: { account_id: 1, to: '', subject: '', body: '' },

        // --- Calendar State ---
        events: [],
        calendarDays: [],
        calendarWeekStart: null,
        eventFormOpen: false,
        eventForm: { title: '', description: '', start_time: '', end_time: '', is_all_day: false },
        editingEventId: null,

        // --- AI State ---
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
            provider_type: '', display_name: '', api_key: '', base_url: '',
            model: '', temperature: 0.7, max_tokens: 1024,
        },

        get unconfiguredProviders() {
            const configured = this.aiConfigs.map(c => c.provider_type);
            return this.availableProviders.filter(p => !configured.includes(p));
        },
        get aiActiveLabel() {
            const active = this.aiConfigs.find(c => c.is_active);
            return active ? active.display_name : null;
        },
        get unreadCount() {
            return this.emails.filter(e => !e.is_read).length;
        },
        get accountOptions() {
            return this.accounts.map(a => ({ value: a.id, label: a.email }));
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

        // --- Init ---
        async init() {
            await this.checkHealth();
            await this.loadAccounts();
            await this.loadEmails();
            await this.loadAiProviders();
            await this.loadAiConfigs();
            await this.loadTriggerTypes();
            await this.loadActionTypes();
            await this.loadAutomationRules();
            await this.loadScheduledJobs();
            this.loading = false;

            this.$watch('page', (val) => {
                if (val === 'calendar') this.loadCalendarEvents();
            });
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
            if (pageId !== 'inbox' && pageId !== 'sent' && pageId !== 'drafts' && pageId !== 'starred') this.composeOpen = false;
            if (['inbox', 'sent', 'drafts', 'starred'].includes(pageId)) {
                this.currentFolder = pageId === 'starred' ? 'STARRED' : pageId.toUpperCase();
                this.loadEmails();
            }
        },

        // --- Accounts ---
        async loadAccounts() {
            try {
                const res = await fetch('/api/ai/configs');
                if (res.ok) {
                    // fallback: seed creates accounts, we'll just track via API
                }
                // Load from seed accounts — just for display
                const h = await fetch('/api/health');
                if (h.ok) this.accounts = [{ id: 1, email: 'nikot@work.com' }, { id: 2, email: 'nikot@personal.com' }];
            } catch (e) {}
        },

        // --- Emails ---
        async loadEmails() {
            try {
                const folder = this.currentFolder === 'STARRED' ? 'STARRED' : this.currentFolder;
                const res = await fetch(`/api/emails?folder=${folder}`);
                if (res.ok) this.emails = await res.json();
            } catch (e) {}
        },

        async selectEmail(email) {
            try {
                const res = await fetch(`/api/emails/${email.id}`);
                if (res.ok) {
                    this.selectedEmail = await res.json();
                    // Update read status in list
                    const idx = this.emails.findIndex(e => e.id === email.id);
                    if (idx >= 0) this.emails[idx].is_read = true;
                }
            } catch (e) {}
        },

        closeEmailDetail() {
            this.selectedEmail = null;
        },

        async toggleStar(email) {
            try {
                const res = await fetch(`/api/emails/${email.id}/toggle-star`, { method: 'POST' });
                if (res.ok) {
                    const data = await res.json();
                    email.is_starred = data.is_starred;
                    if (this.selectedEmail && this.selectedEmail.id === email.id) {
                        this.selectedEmail.is_starred = data.is_starred;
                    }
                }
            } catch (e) {}
        },

        async toggleRead(email) {
            try {
                const res = await fetch(`/api/emails/${email.id}/toggle-read`, { method: 'POST' });
                if (res.ok) {
                    const data = await res.json();
                    email.is_read = data.is_read;
                }
            } catch (e) {}
        },

        async deleteEmail(emailId) {
            try {
                const res = await fetch(`/api/emails/${emailId}`, { method: 'DELETE' });
                if (res.ok) {
                    this.emails = this.emails.filter(e => e.id !== emailId);
                    if (this.selectedEmail && this.selectedEmail.id === emailId) this.selectedEmail = null;
                }
            } catch (e) {}
        },

        openCompose() {
            this.composeForm = { account_id: this.accounts[0]?.id || 1, to: '', subject: '', body: '' };
            this.composeOpen = true;
        },

        closeCompose() {
            this.composeOpen = false;
        },

        async sendEmail() {
            try {
                const res = await fetch('/api/emails/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.composeForm),
                });
                if (res.ok) {
                    this.closeCompose();
                    this.navigate('sent');
                }
            } catch (e) {}
        },

        async saveDraft() {
            try {
                const res = await fetch('/api/emails/draft', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ...this.composeForm, to: this.composeForm.to || 'draft@local' }),
                });
                if (res.ok) {
                    this.closeCompose();
                    this.navigate('drafts');
                }
            } catch (e) {}
        },

        async seedData() {
            try {
                const res = await fetch('/api/seed', { method: 'POST' });
                if (res.ok) {
                    await this.loadEmails();
                    this.currentFolder = 'INBOX';
                    this.page = 'inbox';
                }
            } catch (e) {}
        },

        // --- Calendar ---
        async loadCalendarEvents() {
            try {
                const now = new Date();
                const start = new Date(now);
                start.setDate(start.getDate() - start.getDay());
                start.setHours(0, 0, 0, 0);
                const end = new Date(start);
                end.setDate(end.getDate() + 7);
                end.setHours(23, 59, 59, 999);

                this.calendarWeekStart = start;

                const res = await fetch(`/api/calendar/events?start=${start.toISOString()}&end=${end.toISOString()}`);
                if (res.ok) this.events = await res.json();

                // Build day grid
                this.calendarDays = [];
                for (let i = 0; i < 7; i++) {
                    const d = new Date(start);
                    d.setDate(d.getDate() + i);
                    const dayEvents = this.events.filter(e => {
                        const es = new Date(e.start_time);
                        return es.toDateString() === d.toDateString();
                    });
                    this.calendarDays.push({ date: d, events: dayEvents });
                }
            } catch (e) {}
        },

        calendarWeekLabel() {
            if (!this.calendarDays.length) return '';
            const s = this.calendarDays[0].date;
            const e = this.calendarDays[6].date;
            return `${s.toLocaleDateString([], { month: 'short', day: 'numeric' })} — ${e.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}`;
        },

        isToday(date) {
            return date.toDateString() === new Date().toDateString();
        },

        openNewEvent(day) {
            const d = new Date(day.date);
            d.setHours(10, 0, 0, 0);
            const end = new Date(d);
            end.setHours(11, 0, 0, 0);
            this.eventForm = {
                title: '', description: '',
                start_time: this.toLocalDatetime(d),
                end_time: this.toLocalDatetime(end),
                is_all_day: false,
            };
            this.editingEventId = null;
            this.eventFormOpen = true;
        },

        editEvent(evt) {
            this.eventForm = {
                title: evt.title, description: evt.description || '',
                start_time: this.toLocalDatetime(new Date(evt.start_time)),
                end_time: this.toLocalDatetime(new Date(evt.end_time)),
                is_all_day: evt.is_all_day,
            };
            this.editingEventId = evt.id;
            this.eventFormOpen = true;
        },

        closeEventForm() {
            this.eventFormOpen = false;
            this.editingEventId = null;
        },

        toLocalDatetime(d) {
            const offset = d.getTimezoneOffset();
            const local = new Date(d.getTime() - offset * 60000);
            return local.toISOString().slice(0, 16);
        },

        async saveEvent() {
            try {
                const payload = {
                    ...this.eventForm,
                    start_time: new Date(this.eventForm.start_time).toISOString(),
                    end_time: new Date(this.eventForm.end_time).toISOString(),
                };
                const url = this.editingEventId
                    ? `/api/calendar/events/${this.editingEventId}`
                    : '/api/calendar/events';
                const method = this.editingEventId ? 'PUT' : 'POST';
                const res = await fetch(url, {
                    method, headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (res.ok) {
                    this.closeEventForm();
                    await this.loadCalendarEvents();
                }
            } catch (e) {}
        },

        async deleteEvent(evtId) {
            try {
                const res = await fetch(`/api/calendar/events/${evtId}`, { method: 'DELETE' });
                if (res.ok) {
                    if (this.editingEventId === evtId) this.closeEventForm();
                    await this.loadCalendarEvents();
                }
            } catch (e) {}
        },

        // --- AI ---
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
                api_key: '', base_url: providerType === 'ollama' ? 'http://localhost:11434' : '',
                model: '', temperature: 0.7, max_tokens: 1024,
            };
            this.aiFormEdit = false;
            this.aiFormOpen = true;
        },
        editAiConfig(cfg) {
            this.aiForm = {
                provider_type: cfg.provider_type, display_name: cfg.display_name,
                api_key: cfg.api_key, base_url: cfg.base_url || '',
                model: cfg.model, temperature: cfg.temperature, max_tokens: cfg.max_tokens,
            };
            this.aiFormEdit = true;
            this.aiFormOpen = true;
        },
        closeAiForm() { this.aiFormOpen = false; this.aiFormEdit = false; },
        async saveAiConfig() {
            this.aiError = '';
            try {
                const url = this.aiFormEdit ? `/api/ai/configs/${this.aiForm.provider_type}` : '/api/ai/configs';
                const method = this.aiFormEdit ? 'PUT' : 'POST';
                const res = await fetch(url, {
                    method, headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.aiForm),
                });
                if (!res.ok) { const err = await res.json(); this.aiError = err.detail || 'Failed to save'; return; }
                this.closeAiForm();
                await this.loadAiConfigs();
            } catch (e) { this.aiError = 'Network error saving config'; }
        },
        async activateAiProvider(providerType) {
            try {
                const res = await fetch(`/api/ai/configs/${providerType}`, {
                    method: 'PUT', headers: { 'Content-Type': 'application/json' },
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
        async aiAction(action) {
            if (!this.aiInput.trim()) return;
            this.aiLoading = true; this.aiResult = ''; this.aiError = '';
            this.aiToneSelector = action === 'draft';
            try {
                let res;
                const opts = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
                if (action === 'draft') res = await fetch('/api/ai/draft', opts({ email_text: this.aiInput, tone: this.aiTone }));
                else if (action === 'summarize') res = await fetch('/api/ai/summarize', opts({ email_text: this.aiInput }));
                else if (action === 'categorize') res = await fetch('/api/ai/categorize', opts({ subject: '', body: this.aiInput }));
                else if (action === 'chat') res = await fetch('/api/ai/chat', opts({ prompt: this.aiInput }));
                if (res && res.ok) { const d = await res.json(); this.aiResult = d.result; this.aiResultProvider = `${d.provider} (${d.model})`; }
                else if (res) { const err = await res.json(); this.aiError = err.detail || 'AI request failed'; }
            } catch (e) { this.aiError = 'Network error during AI request'; }
            finally { this.aiLoading = false; }
        },
        copyAiResult() { navigator.clipboard?.writeText(this.aiResult); },

        // --- Automation ---
        async loadAutomationRules() { try { const r = await fetch('/api/automation/rules'); if (r.ok) this.automationRules = await r.json(); } catch (e) {} },
        async loadTriggerTypes() { try { const r = await fetch('/api/automation/trigger-types'); if (r.ok) this.triggerTypes = await r.json(); } catch (e) {} },
        async loadActionTypes() { try { const r = await fetch('/api/automation/action-types'); if (r.ok) this.actionTypes = await r.json(); } catch (e) {} },
        async loadScheduledJobs() { try { const r = await fetch('/api/automation/scheduler/jobs'); if (r.ok) this.scheduledJobs = await r.json(); } catch (e) {} },
        openNewRule() {
            this.ruleForm = { name: '', description: '', trigger_type: 'new_email', trigger_config: {}, action_type: 'auto_reply', action_config: {}, cron_schedule: '', is_enabled: true, account_id: null };
            this.ruleFormEdit = false; this.ruleFormOpen = true;
        },
        editRule(rule) {
            this.ruleForm = { name: rule.name, description: rule.description || '', trigger_type: rule.trigger_type, trigger_config: rule.trigger_config || {}, action_type: rule.action_type, action_config: rule.action_config || {}, cron_schedule: rule.cron_schedule || '', is_enabled: rule.is_enabled, account_id: rule.account_id };
            this.ruleFormEdit = true; this.ruleFormEditId = rule.id; this.ruleFormOpen = true;
        },
        closeRuleForm() { this.ruleFormOpen = false; this.ruleFormEdit = false; this.ruleFormEditId = null; },
        async saveRule() {
            try {
                const payload = { ...this.ruleForm };
                if (!payload.cron_schedule) payload.cron_schedule = null;
                const url = this.ruleFormEdit ? `/api/automation/rules/${this.ruleFormEditId}` : '/api/automation/rules';
                const method = this.ruleFormEdit ? 'PUT' : 'POST';
                const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (res.ok) { this.closeRuleForm(); await this.loadAutomationRules(); await this.loadScheduledJobs(); }
            } catch (e) {}
        },
        async deleteRule(ruleId) { try { const r = await fetch(`/api/automation/rules/${ruleId}`, { method: 'DELETE' }); if (r.ok) { await this.loadAutomationRules(); await this.loadScheduledJobs(); } } catch (e) {} },
        async toggleRule(ruleId) { try { const r = await fetch(`/api/automation/rules/${ruleId}/toggle`, { method: 'POST' }); if (r.ok) { await this.loadAutomationRules(); await this.loadScheduledJobs(); } } catch (e) {} },
        triggerTypeLabel(type) { const l = { new_email: '📩 New Email', keyword_match: '🔑 Keyword Match', cron_schedule: '⏰ Cron Schedule' }; return l[type] || type; },
        actionTypeLabel(type) { const l = { auto_reply: '✉️ Auto-Reply', categorize: '🏷️ Categorize', mark_read: '✔️ Mark Read', star: '⭐ Star', forward: '📤 Forward' }; return l[type] || type; },

        // --- Utils ---
        formatDate(dateStr) {
            if (!dateStr) return '';
            const d = new Date(dateStr);
            const now = new Date();
            if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const yesterday = new Date(now); yesterday.setDate(yesterday.getDate() - 1);
            if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
            return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
        },
        truncate(str, len) { return str && str.length > len ? str.slice(0, len) + '...' : str || ''; },
        dayName(d) { return d.toLocaleDateString([], { weekday: 'short' }); },
        dayNum(d) { return d.getDate(); },
        hourLabel(d) { return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); },
    }));
});
