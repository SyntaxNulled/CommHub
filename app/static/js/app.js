// CommHub Frontend — Alpine.js
document.addEventListener('alpine:init', () => {
    Alpine.data('app', () => ({
        // --- Navigation ---
        page: 'inbox',
        health: null,
        loading: true,
        darkMode: localStorage.getItem('commhub-dark') === 'true',
        sidebarOpen: false, // mobile drawer

        mailLinks: [
            { id: 'inbox', label: 'Inbox', icon: 'inbox' },
            { id: 'sent', label: 'Sent', icon: 'sent' },
            { id: 'drafts', label: 'Drafts', icon: 'draft' },
            { id: 'starred', label: 'Starred', icon: 'star' },
            { id: 'calendar', label: 'Calendar', icon: 'calendar' },
        ],
        toolLinks: [
            { id: 'automation', label: 'Automation', icon: 'automation' },
            { id: 'settings', label: 'Settings', icon: 'settings' },
        ],

        // --- Toasts ---
        toasts: [],
        _toastId: 0,

        // --- Email State ---
        accounts: [],
        emails: [],
        selectedEmail: null,
        currentFolder: 'INBOX',
        composeOpen: false,
        composeForm: { account_id: null, to: '', subject: '', body: '' },
        sending: false,
        searchQuery: '',
        searchFilter: 'all',
        shortcutsOpen: false,
        currentPage: 1,
        pageSize: 20,
        totalEmails: 0,
        unreadTotal: 0,
        emailsLoading: false,
        confirmDelete: null, // { type: 'email'|'event'|'rule'|'aiConfig', id, label }
        _emailReq: 0,
        _searchTimer: null,
        _listenerAttached: false,

        // --- Calendar State ---
        events: [],
        calendarDays: [],
        calendarWeekStart: null,
        calendarOffsetWeeks: 0,
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
        aiCopied: false,

        // AI Config
        aiConfigs: [],
        availableProviders: [],
        aiFormOpen: false,
        aiFormEdit: false,
        aiForm: {
            provider_type: '', display_name: '', api_key: '', base_url: '',
            model: '', temperature: 0.7, max_tokens: 1024,
        },
        aiFormError: '',
        aiFormSaving: false,

        // --- Automation State ---
        automationRules: [],
        triggerTypes: [],
        actionTypes: [],
        ruleFormOpen: false,
        ruleFormEdit: false,
        ruleFormEditId: null,
        ruleFormSaving: false,
        ruleForm: {
            name: '', description: '', trigger_type: 'new_email',
            trigger_config: {}, action_type: 'auto_reply',
            action_config: {}, cron_schedule: '', is_enabled: true, account_id: null,
        },

        // --- Computed ---
        get filteredEmails() {
            let list = this.emails;
            if (this.searchFilter === 'unread') list = list.filter(e => !e.is_read);
            else if (this.searchFilter === 'read') list = list.filter(e => e.is_read);
            else if (this.searchFilter === 'starred') list = list.filter(e => e.is_starred);
            return list;
        },
        get totalPages() {
            return Math.max(1, Math.ceil(this.totalEmails / this.pageSize));
        },
        get unconfiguredProviders() {
            const configured = this.aiConfigs.map(c => c.provider_type);
            return this.availableProviders.filter(p => !configured.includes(p));
        },
        get aiActiveLabel() {
            const active = this.aiConfigs.find(c => c.is_active);
            return active ? active.display_name : null;
        },
        get accountOptions() {
            return this.accounts.map(a => ({ value: a.id, label: a.email }));
        },
        get pageTitle() {
            const titles = { inbox: 'Inbox', sent: 'Sent', drafts: 'Drafts', starred: 'Starred', calendar: 'Calendar', automation: 'Automation', settings: 'Settings' };
            return titles[this.page] || 'CommHub';
        },
        get isMailPage() {
            return ['inbox', 'sent', 'drafts', 'starred'].includes(this.page);
        },

        // --- Init (Alpine calls this automatically — do NOT also use x-init) ---
        async init() {
            if (this.darkMode) document.documentElement.classList.add('dark');
            if (!this._listenerAttached) {
                window.addEventListener('keydown', (e) => this.handleKeydown(e));
                this._listenerAttached = true;
            }

            await this.checkHealth();
            // Independent loads in parallel — sequential awaits doubled startup time
            await Promise.all([
                this.loadAccounts(),
                this.loadEmails(),
                this.loadUnreadCount(),
                this.loadAiProviders(),
                this.loadAiConfigs(),
                this.loadTriggerTypes(),
                this.loadActionTypes(),
                this.loadAutomationRules(),
            ]);
            this.loading = false;

            this.$watch('page', (val) => {
                if (val === 'calendar') this.loadCalendarEvents();
            });
            this.$watch('darkMode', (val) => {
                document.documentElement.classList.toggle('dark', val);
                localStorage.setItem('commhub-dark', val);
            });
            this.$watch('searchQuery', () => {
                clearTimeout(this._searchTimer);
                this._searchTimer = setTimeout(() => {
                    this.currentPage = 1;
                    this.loadEmails();
                }, 300);
            });
        },

        // --- Toasts ---
        toast(message, type = 'info') {
            const id = ++this._toastId;
            this.toasts.push({ id, message, type });
            setTimeout(() => this.dismissToast(id), 4000);
        },
        dismissToast(id) {
            this.toasts = this.toasts.filter(t => t.id !== id);
        },

        async checkHealth() {
            try {
                const res = await fetch('/api/health');
                this.health = await res.json();
            } catch (e) {
                this.toast('Cannot connect to the CommHub backend', 'error');
            }
        },

        navigate(pageId) {
            this.page = pageId;
            this.selectedEmail = null;
            this.sidebarOpen = false;
            this.searchQuery = '';
            this.searchFilter = 'all';
            if (pageId !== 'settings') this.closeAiForm();
            if (pageId !== 'automation') this.closeRuleForm();
            if (!this.isMailPage) this.composeOpen = false;
            if (this.isMailPage) {
                this.currentFolder = pageId === 'starred' ? 'STARRED' : pageId.toUpperCase();
                this.currentPage = 1;
                this.loadEmails();
            }
        },

        // --- Keyboard shortcuts ---
        handleKeydown(e) {
            // Never hijack browser/system shortcuts (Ctrl+C, Cmd+R, ...)
            if (e.ctrlKey || e.metaKey || e.altKey) return;

            const tag = e.target.tagName;
            const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable;

            if (e.key === 'Escape') {
                if (this.confirmDelete) { this.confirmDelete = null; return; }
                if (this.shortcutsOpen) { this.shortcutsOpen = false; return; }
                if (this.composeOpen) { this.closeCompose(); return; }
                if (this.eventFormOpen) { this.closeEventForm(); return; }
                if (this.aiPanelOpen) { this.aiPanelOpen = false; return; }
                if (this.selectedEmail) { this.closeEmailDetail(); return; }
                return;
            }

            if (isInput) return;

            switch (e.key) {
                case '?':
                    e.preventDefault();
                    this.shortcutsOpen = !this.shortcutsOpen;
                    break;
                case '/':
                    e.preventDefault();
                    this.focusSearch();
                    break;
                case 'c':
                    if (this.isMailPage) { e.preventDefault(); this.openCompose(); }
                    break;
                case 'r':
                    if (this.selectedEmail) { e.preventDefault(); this.replyToSelected(); }
                    break;
                case 'j':
                case 'ArrowDown':
                    if (this.isMailPage) { e.preventDefault(); this.navigateEmail(1); }
                    break;
                case 'k':
                case 'ArrowUp':
                    if (this.isMailPage) { e.preventDefault(); this.navigateEmail(-1); }
                    break;
            }
        },

        focusSearch() {
            this.$nextTick(() => {
                const inputs = document.querySelectorAll('input[type="search"]');
                for (const el of inputs) {
                    if (el.offsetParent !== null) { el.focus(); return; }
                }
            });
        },

        navigateEmail(direction) {
            const list = this.filteredEmails;
            if (!list.length) return;
            let idx = this.selectedEmail ? list.findIndex(e => e.id === this.selectedEmail.id) : -1;
            idx += direction;
            if (idx < 0) idx = 0;
            if (idx >= list.length) idx = list.length - 1;
            this.selectEmail(list[idx]);
        },

        // --- Accounts ---
        async loadAccounts() {
            try {
                const res = await fetch('/api/accounts');
                if (res.ok) this.accounts = await res.json();
            } catch (e) { /* surfaced via seed CTA if empty */ }
        },

        // --- Emails ---
        async loadEmails() {
            const reqId = ++this._emailReq;
            this.emailsLoading = true;
            try {
                const params = new URLSearchParams({
                    folder: this.currentFolder,
                    page: this.currentPage,
                    page_size: this.pageSize,
                });
                if (this.searchQuery.trim()) params.set('q', this.searchQuery.trim());
                const res = await fetch(`/api/emails?${params}`);
                if (reqId !== this._emailReq) return; // stale response — a newer request superseded this one
                if (res.ok) {
                    this.emails = await res.json();
                    this.totalEmails = parseInt(res.headers.get('X-Total-Count') || '0');
                } else {
                    this.toast('Failed to load emails', 'error');
                }
            } catch (e) {
                if (reqId === this._emailReq) this.toast('Network error loading emails', 'error');
            } finally {
                if (reqId === this._emailReq) this.emailsLoading = false;
            }
        },

        async loadUnreadCount() {
            try {
                const res = await fetch('/api/emails/unread-count');
                if (res.ok) this.unreadTotal = (await res.json()).unread;
            } catch (e) {}
        },

        async selectEmail(email) {
            this.selectedEmail = email;
            if (!email.is_read) {
                try {
                    const res = await fetch(`/api/emails/${email.id}/mark-read`, { method: 'POST' });
                    if (res.ok) {
                        email.is_read = true;
                        this.loadUnreadCount();
                    }
                } catch (e) {}
            }
        },

        toggleDarkMode() { this.darkMode = !this.darkMode; },
        closeEmailDetail() { this.selectedEmail = null; },

        async toggleStar(email) {
            try {
                const res = await fetch(`/api/emails/${email.id}/toggle-star`, { method: 'POST' });
                if (res.ok) {
                    const data = await res.json();
                    email.is_starred = data.is_starred;
                    if (this.selectedEmail?.id === email.id) this.selectedEmail.is_starred = data.is_starred;
                } else {
                    this.toast('Failed to update star', 'error');
                }
            } catch (e) { this.toast('Network error', 'error'); }
        },

        requestDelete(type, id, label) {
            this.confirmDelete = { type, id, label };
        },

        async executeDelete() {
            const { type, id } = this.confirmDelete || {};
            this.confirmDelete = null;
            if (type === 'email') await this.deleteEmail(id);
            else if (type === 'event') await this.deleteEvent(id);
            else if (type === 'rule') await this.deleteRule(id);
            else if (type === 'aiConfig') await this.deleteAiConfig(id);
        },

        async deleteEmail(emailId) {
            try {
                const res = await fetch(`/api/emails/${emailId}`, { method: 'DELETE' });
                if (res.ok) {
                    this.emails = this.emails.filter(e => e.id !== emailId);
                    this.totalEmails = Math.max(0, this.totalEmails - 1);
                    if (this.selectedEmail?.id === emailId) this.selectedEmail = null;
                    this.loadUnreadCount();
                    this.toast('Email deleted', 'success');
                } else {
                    this.toast('Failed to delete email', 'error');
                }
            } catch (e) { this.toast('Network error deleting email', 'error'); }
        },

        openCompose(prefill = {}) {
            this.composeForm = {
                account_id: this.accounts[0]?.id ?? null,
                to: prefill.to || '',
                subject: prefill.subject || '',
                body: prefill.body || '',
            };
            this.composeOpen = true;
            this.$nextTick(() => document.getElementById('compose-to')?.focus());
        },

        replyToSelected() {
            if (!this.selectedEmail) return;
            const subj = this.selectedEmail.subject || '';
            this.openCompose({
                to: this.selectedEmail.from_address,
                subject: subj.startsWith('Re: ') ? subj : `Re: ${subj}`,
            });
        },

        closeCompose(force = false) {
            const dirty = this.composeForm.to || this.composeForm.subject || this.composeForm.body;
            if (dirty && !force) {
                if (!window.confirm('Discard this draft?')) return;
            }
            this.composeOpen = false;
        },

        async sendEmail() {
            if (this.sending) return;
            if (!this.composeForm.to.trim()) { this.toast('Add a recipient first', 'error'); return; }
            if (!this.composeForm.account_id) { this.toast('No account available — seed demo data first', 'error'); return; }
            this.sending = true;
            try {
                const res = await fetch('/api/emails/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.composeForm),
                });
                if (res.ok) {
                    this.composeOpen = false;
                    this.toast('Email sent', 'success');
                    this.navigate('sent');
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.toast(err.detail || 'Failed to send email', 'error');
                }
            } catch (e) {
                this.toast('Network error sending email', 'error');
            } finally {
                this.sending = false;
            }
        },

        async saveDraft() {
            if (this.sending) return;
            if (!this.composeForm.account_id) { this.toast('No account available — seed demo data first', 'error'); return; }
            this.sending = true;
            try {
                const res = await fetch('/api/emails/draft', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.composeForm),
                });
                if (res.ok) {
                    this.composeOpen = false;
                    this.toast('Draft saved', 'success');
                    this.navigate('drafts');
                } else {
                    this.toast('Failed to save draft', 'error');
                }
            } catch (e) {
                this.toast('Network error saving draft', 'error');
            } finally {
                this.sending = false;
            }
        },

        nextPage() {
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
                this.selectedEmail = null;
                this.loadEmails();
            }
        },
        prevPage() {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.selectedEmail = null;
                this.loadEmails();
            }
        },

        async seedData() {
            try {
                const res = await fetch('/api/seed', { method: 'POST' });
                if (res.ok) {
                    this.currentFolder = 'INBOX';
                    this.page = 'inbox';
                    this.currentPage = 1;
                    await Promise.all([this.loadEmails(), this.loadAccounts(), this.loadUnreadCount()]);
                    this.toast('Demo data loaded', 'success');
                } else {
                    this.toast('Failed to seed demo data', 'error');
                }
            } catch (e) { this.toast('Network error seeding data', 'error'); }
        },

        // --- Calendar ---
        async loadCalendarEvents() {
            try {
                const now = new Date();
                const start = new Date(now);
                start.setDate(start.getDate() - start.getDay() + this.calendarOffsetWeeks * 7);
                start.setHours(0, 0, 0, 0);
                const end = new Date(start);
                end.setDate(end.getDate() + 7);
                end.setHours(23, 59, 59, 999);

                this.calendarWeekStart = start;

                const res = await fetch(`/api/calendar/events?start=${start.toISOString()}&end=${end.toISOString()}`);
                if (res.ok) this.events = await res.json();
                else { this.toast('Failed to load calendar', 'error'); return; }

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
            } catch (e) { this.toast('Network error loading calendar', 'error'); }
        },

        calendarPrevWeek() { this.calendarOffsetWeeks--; this.loadCalendarEvents(); },
        calendarNextWeek() { this.calendarOffsetWeeks++; this.loadCalendarEvents(); },
        calendarToday() { this.calendarOffsetWeeks = 0; this.loadCalendarEvents(); },

        calendarWeekLabel() {
            if (!this.calendarDays.length) return '';
            const s = this.calendarDays[0].date;
            const e = this.calendarDays[6].date;
            return `${s.toLocaleDateString([], { month: 'short', day: 'numeric' })} — ${e.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}`;
        },

        isToday(date) { return date.toDateString() === new Date().toDateString(); },

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
            this.$nextTick(() => document.getElementById('event-title')?.focus());
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
            if (!this.eventForm.title.trim()) { this.toast('Event needs a title', 'error'); return; }
            try {
                const payload = {
                    ...this.eventForm,
                    account_id: this.accounts[0]?.id ?? 1,
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
                    this.toast(this.editingEventId ? 'Event updated' : 'Event created', 'success');
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.toast(err.detail || 'Failed to save event', 'error');
                }
            } catch (e) { this.toast('Network error saving event', 'error'); }
        },

        async deleteEvent(evtId) {
            try {
                const res = await fetch(`/api/calendar/events/${evtId}`, { method: 'DELETE' });
                if (res.ok) {
                    if (this.editingEventId === evtId) this.closeEventForm();
                    await this.loadCalendarEvents();
                    this.toast('Event deleted', 'success');
                } else {
                    this.toast('Failed to delete event', 'error');
                }
            } catch (e) { this.toast('Network error deleting event', 'error'); }
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
            this.aiFormError = '';
        },
        editAiConfig(cfg) {
            this.aiForm = {
                provider_type: cfg.provider_type, display_name: cfg.display_name,
                api_key: '', // never round-trip the secret; blank = keep existing
                base_url: cfg.base_url || '',
                model: cfg.model, temperature: cfg.temperature, max_tokens: cfg.max_tokens,
            };
            this.aiFormEdit = true;
            this.aiFormOpen = true;
            this.aiFormError = '';
        },
        closeAiForm() { this.aiFormOpen = false; this.aiFormEdit = false; this.aiFormError = ''; },
        async saveAiConfig() {
            if (this.aiFormSaving) return;
            this.aiFormError = '';
            this.aiFormSaving = true;
            try {
                const url = this.aiFormEdit ? `/api/ai/configs/${this.aiForm.provider_type}` : '/api/ai/configs';
                const method = this.aiFormEdit ? 'PUT' : 'POST';
                const res = await fetch(url, {
                    method, headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.aiForm),
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    this.aiFormError = err.detail || 'Failed to save';
                    return;
                }
                this.closeAiForm();
                await this.loadAiConfigs();
                this.toast('AI provider saved', 'success');
            } catch (e) { this.aiFormError = 'Network error saving config'; }
            finally { this.aiFormSaving = false; }
        },
        async activateAiProvider(providerType) {
            try {
                const res = await fetch(`/api/ai/configs/${providerType}`, {
                    method: 'PUT', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_active: true }),
                });
                if (res.ok) {
                    await this.loadAiConfigs();
                    this.toast(`${providerType} is now the active provider`, 'success');
                }
            } catch (e) { this.toast('Failed to activate provider', 'error'); }
        },
        async deleteAiConfig(providerType) {
            try {
                const res = await fetch(`/api/ai/configs/${providerType}`, { method: 'DELETE' });
                if (res.ok) {
                    await this.loadAiConfigs();
                    this.toast('Provider removed', 'success');
                } else {
                    this.toast('Failed to remove provider', 'error');
                }
            } catch (e) { this.toast('Network error', 'error'); }
        },
        async aiAction(action) {
            if (!this.aiInput.trim() || this.aiLoading) return;
            this.aiLoading = true; this.aiResult = ''; this.aiError = ''; this.aiCopied = false;
            try {
                let res;
                const opts = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
                if (action === 'draft') res = await fetch('/api/ai/draft', opts({ email_text: this.aiInput, tone: this.aiTone }));
                else if (action === 'summarize') res = await fetch('/api/ai/summarize', opts({ email_text: this.aiInput }));
                else if (action === 'categorize') res = await fetch('/api/ai/categorize', opts({ subject: '', body: this.aiInput }));
                else if (action === 'chat') res = await fetch('/api/ai/chat', opts({ prompt: this.aiInput }));
                if (res && res.ok) {
                    const d = await res.json();
                    this.aiResult = d.result;
                    this.aiResultProvider = `${d.provider} (${d.model})`;
                } else if (res) {
                    const err = await res.json().catch(() => ({}));
                    this.aiError = err.detail || 'AI request failed';
                }
            } catch (e) { this.aiError = 'Network error during AI request'; }
            finally { this.aiLoading = false; }
        },
        async copyAiResult() {
            try {
                await navigator.clipboard.writeText(this.aiResult);
                this.aiCopied = true;
                setTimeout(() => this.aiCopied = false, 2000);
            } catch (e) { this.toast('Clipboard unavailable', 'error'); }
        },

        // --- Automation ---
        async loadAutomationRules() {
            try { const r = await fetch('/api/automation/rules'); if (r.ok) this.automationRules = await r.json(); } catch (e) {}
        },
        async loadTriggerTypes() {
            try { const r = await fetch('/api/automation/trigger-types'); if (r.ok) this.triggerTypes = await r.json(); } catch (e) {}
        },
        async loadActionTypes() {
            try { const r = await fetch('/api/automation/action-types'); if (r.ok) this.actionTypes = await r.json(); } catch (e) {}
        },
        openNewRule() {
            this.ruleForm = { name: '', description: '', trigger_type: 'new_email', trigger_config: {}, action_type: 'auto_reply', action_config: {}, cron_schedule: '', is_enabled: true, account_id: null };
            this.ruleFormEdit = false; this.ruleFormEditId = null; this.ruleFormOpen = true;
            this.$nextTick(() => document.getElementById('rule-name')?.focus());
        },
        editRule(rule) {
            this.ruleForm = { name: rule.name, description: rule.description || '', trigger_type: rule.trigger_type, trigger_config: rule.trigger_config || {}, action_type: rule.action_type, action_config: rule.action_config || {}, cron_schedule: rule.cron_schedule || '', is_enabled: rule.is_enabled, account_id: rule.account_id };
            this.ruleFormEdit = true; this.ruleFormEditId = rule.id; this.ruleFormOpen = true;
        },
        closeRuleForm() { this.ruleFormOpen = false; this.ruleFormEdit = false; this.ruleFormEditId = null; },
        async saveRule() {
            if (this.ruleFormSaving) return;
            if (!this.ruleForm.name.trim()) { this.toast('Rule needs a name', 'error'); return; }
            this.ruleFormSaving = true;
            try {
                const payload = { ...this.ruleForm };
                if (!payload.cron_schedule) payload.cron_schedule = null;
                const url = this.ruleFormEdit ? `/api/automation/rules/${this.ruleFormEditId}` : '/api/automation/rules';
                const method = this.ruleFormEdit ? 'PUT' : 'POST';
                const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (res.ok) {
                    this.closeRuleForm();
                    await this.loadAutomationRules();
                    this.toast(this.ruleFormEdit ? 'Rule updated' : 'Rule created', 'success');
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.toast(err.detail || 'Failed to save rule', 'error');
                }
            } catch (e) { this.toast('Network error saving rule', 'error'); }
            finally { this.ruleFormSaving = false; }
        },
        async deleteRule(ruleId) {
            try {
                const r = await fetch(`/api/automation/rules/${ruleId}`, { method: 'DELETE' });
                if (r.ok) { await this.loadAutomationRules(); this.toast('Rule deleted', 'success'); }
                else this.toast('Failed to delete rule', 'error');
            } catch (e) { this.toast('Network error', 'error'); }
        },
        async toggleRule(ruleId) {
            try {
                const r = await fetch(`/api/automation/rules/${ruleId}/toggle`, { method: 'POST' });
                if (r.ok) await this.loadAutomationRules();
                else this.toast('Failed to toggle rule', 'error');
            } catch (e) { this.toast('Network error', 'error'); }
        },
        triggerTypeLabel(type) {
            const l = { new_email: 'New Email', keyword_match: 'Keyword Match', cron_schedule: 'Cron Schedule' };
            return l[type] || type;
        },
        actionTypeLabel(type) {
            const l = { auto_reply: 'Auto-Reply', categorize: 'Categorize', mark_read: 'Mark Read', star: 'Star', forward: 'Forward' };
            return l[type] || type;
        },

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
        initials(nameOrEmail) {
            if (!nameOrEmail) return '?';
            const name = nameOrEmail.split('@')[0];
            const parts = name.split(/[\s._-]+/).filter(Boolean);
            if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
            return name.slice(0, 2).toUpperCase();
        },
        avatarColor(str) {
            const colors = ['bg-blue-600', 'bg-indigo-600', 'bg-violet-600', 'bg-emerald-600', 'bg-rose-600', 'bg-amber-600', 'bg-cyan-600', 'bg-fuchsia-600'];
            let hash = 0;
            for (let i = 0; i < (str || '').length; i++) hash = (hash * 31 + str.charCodeAt(i)) | 0;
            return colors[Math.abs(hash) % colors.length];
        },
        dayName(d) { return d.toLocaleDateString([], { weekday: 'short' }); },
        dayNum(d) { return d.getDate(); },

        iconSVG(name) {
            const icons = {
                inbox: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/></svg>',
                sent: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>',
                draft: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>',
                star: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
                calendar: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>',
                automation: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>',
                settings: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>',
            };
            return icons[name] || '';
        },
    }));
});
