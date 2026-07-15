// CommHub Frontend — Alpine.js + vanilla JS
document.addEventListener('alpine:init', () => {
    Alpine.data('app', () => ({
        // Navigation
        page: 'inbox',
        health: null,
        loading: true,
        error: null,
        darkMode: localStorage.getItem('commhub-dark') === 'true',

        sidebarLinks: [
            { id: 'inbox', label: 'Inbox', icon: 'inbox' },
            { id: 'sent', label: 'Sent', icon: 'sent' },
            { id: 'drafts', label: 'Drafts', icon: 'draft' },
            { id: 'starred', label: 'Starred', icon: 'star' },
            { id: 'calendar', label: 'Calendar', icon: 'calendar' },
            { id: 'automation', label: 'Automation', icon: 'automation' },
            { id: 'settings', label: 'Settings', icon: 'settings' },
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
            if (this.darkMode) document.documentElement.classList.add('dark');
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
            this.$watch('darkMode', (val) => {
                document.documentElement.classList.toggle('dark', val);
                localStorage.setItem('commhub-dark', val);
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

        toggleDarkMode() {
            this.darkMode = !this.darkMode;
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
        iconSVG(name) {
            const icons = {
                inbox: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/></svg>',
                sent: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>',
                draft: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>',
                star: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
                calendar: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>',
                automation: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>',
                settings: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>',
                compose: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>',
                search: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>',
                moon: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>',
                sun: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>',
                trash: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>',
                reply: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg>',
                plus: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>',
            };
            return icons[name] || '';
        },
        dayName(d) { return d.toLocaleDateString([], { weekday: 'short' }); },
        dayNum(d) { return d.getDate(); },
        hourLabel(d) { return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); },
    }));
});
