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
        calendarView: 'week', // 'day' | 'week' | 'month' | 'agenda'
        calendarOffsetDays: 0, // for day/week view (in days)
        calendarOffsetMonths: 0, // for month view
        calendarCategories: [],
        selectedEvent: null, // read-only detail panel
        eventFormOpen: false,
        eventForm: { title: '', description: '', start_time: '', end_time: '', is_all_day: false, category: 'other', rrule: '' },
        editingEventId: null,
        miniCalendarDate: new Date(),
        calendarFilter: 'all', // category filter
        calendarLoading: false,
        _calendarReq: 0,
        recurrencePresets: [
            { label: 'None', value: '' },
            { label: 'Daily', value: 'FREQ=DAILY;COUNT=30' },
            { label: 'Weekdays', value: 'FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;COUNT=60' },
            { label: 'Weekly', value: 'FREQ=WEEKLY;COUNT=52' },
            { label: 'Bi-weekly', value: 'FREQ=WEEKLY;INTERVAL=2;COUNT=26' },
            { label: 'Monthly', value: 'FREQ=MONTHLY;COUNT=12' },
            { label: 'Yearly', value: 'FREQ=YEARLY;COUNT=5' },
        ],

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
            id: null, provider_type: '', display_name: '', api_key: '', base_url: '',
            model: '', temperature: 0.7, max_tokens: 1024,
        },
        aiFormError: '',
        aiFormSaving: false,

        // AI Organization
        aiOrganizeOpen: false,
        aiOrganizeLoading: false,
        aiOrganizeSuggestions: [],
        aiOrganizeApplyAll: [],

        // --- Folder State ---
        folders: [],
        folderFormOpen: false,
        folderFormEdit: false,
        folderFormEditId: null,
        folderFormSaving: false,
        folderForm: { name: '', color: 'blue', icon: 'folder' },
        folderColors: ['blue', 'emerald', 'violet', 'red', 'amber', 'pink', 'gray', 'cyan', 'indigo', 'rose'],
        folderColorMap: {
            blue: '#2563EB', emerald: '#10B981', violet: '#8B5CF6', red: '#DC2626',
            amber: '#F59E0B', pink: '#EC4899', gray: '#6B7280', cyan: '#06B6D4',
            indigo: '#6366F1', rose: '#F43F5E',
        },
        folderIcons: ['folder', 'inbox', 'star', 'calendar', 'briefcase', 'user', 'tag', 'bell', 'document', 'code'],

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
            // Built-in providers are only addable once; custom can be added repeatedly
            const configuredBuiltins = this.aiConfigs
                .filter(c => c.provider_type !== 'custom')
                .map(c => c.provider_type);
            return this.availableProviders.filter(p => p !== 'custom' && !configuredBuiltins.includes(p));
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
            if (titles[this.page]) return titles[this.page];
            const folder = this.folders.find(f => f.normalized_name === this.currentFolder);
            return folder ? folder.name : 'CommHub';
        },
        get isMailPage() {
            const mailPages = ['inbox', 'sent', 'drafts', 'starred'];
            if (mailPages.includes(this.page)) return true;
            return this.folders.some(f => f.normalized_name === this.page.toUpperCase());
        },
        get calendarEventColor() {
            return (category) => {
                const cat = this.calendarCategories.find(c => c.name === category);
                return cat?.color || '#3B82F6';
            };
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
                this.loadFolders(),
                this.loadEmails(),
                this.loadUnreadCount(),
                this.loadAiProviders(),
                this.loadAiConfigs(),
                this.loadTriggerTypes(),
                this.loadActionTypes(),
                this.loadAutomationRules(),
                this.loadCalendarCategories(),
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
            this.selectedEvent = null;
            this.aiOrganizeOpen = false;
            this.closeFolderForm();
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
                if (this.aiOrganizeOpen) { this.aiOrganizeOpen = false; return; }
                if (this.aiPanelOpen) { this.aiPanelOpen = false; return; }
                if (this.selectedEvent) { this.selectedEvent = null; return; }
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
            else if (type === 'folder') await this.deleteFolder(id);
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
        async loadCalendarCategories() {
            try {
                const res = await fetch('/api/calendar/categories');
                if (res.ok) this.calendarCategories = await res.json();
            } catch (e) {}
        },

        _calendarRange() {
            const now = new Date();
            const start = new Date(now);
            const end = new Date(start);
            if (this.calendarView === 'day') {
                start.setDate(start.getDate() + this.calendarOffsetDays);
                start.setHours(0, 0, 0, 0);
                end.setDate(end.getDate() + this.calendarOffsetDays);
                end.setHours(23, 59, 59, 999);
            } else if (this.calendarView === 'week') {
                start.setDate(start.getDate() - start.getDay() + this.calendarOffsetDays);
                start.setHours(0, 0, 0, 0);
                end.setDate(start.getDate() + 7);
                end.setHours(23, 59, 59, 999);
            } else if (this.calendarView === 'month') {
                const monthAnchor = new Date(start);
                monthAnchor.setMonth(monthAnchor.getMonth() + this.calendarOffsetMonths);
                monthAnchor.setDate(1);
                start.setDate(1);
                start.setMonth(monthAnchor.getMonth());
                start.setFullYear(monthAnchor.getFullYear());
                start.setDate(start.getDate() - start.getDay()); // Sunday before month start
                start.setHours(0, 0, 0, 0);
                end.setDate(start.getDate() + 42); // 6 weeks
                end.setHours(23, 59, 59, 999);
            } else { // agenda
                start.setDate(start.getDate() + this.calendarOffsetDays);
                start.setHours(0, 0, 0, 0);
                end.setMonth(end.getMonth() + 1);
                end.setHours(23, 59, 59, 999);
            }
            this.miniCalendarDate = new Date(start);
            return { start, end };
        },

        async loadCalendarEvents() {
            const reqId = ++this._calendarReq;
            this.calendarLoading = true;
            try {
                const { start, end } = this._calendarRange();
                const params = new URLSearchParams({
                    start: start.toISOString(),
                    end: end.toISOString(),
                });
                if (this.calendarFilter !== 'all') params.set('category', this.calendarFilter);
                const res = await fetch(`/api/calendar/events?${params}`);
                if (reqId !== this._calendarReq) return;
                if (res.ok) this.events = await res.json();
                else { this.toast('Failed to load calendar', 'error'); return; }
            } catch (e) {
                if (reqId === this._calendarReq) this.toast('Network error loading calendar', 'error');
            } finally {
                if (reqId === this._calendarReq) this.calendarLoading = false;
            }
        },

        setCalendarView(view) {
            this.calendarView = view;
            this.calendarOffsetDays = 0;
            this.calendarOffsetMonths = 0;
            this.selectedEvent = null;
            this.loadCalendarEvents();
        },

        calendarPrev() {
            if (this.calendarView === 'month') this.calendarOffsetMonths--;
            else this.calendarOffsetDays -= (this.calendarView === 'week' ? 7 : 1);
            this.loadCalendarEvents();
        },
        calendarNext() {
            if (this.calendarView === 'month') this.calendarOffsetMonths++;
            else this.calendarOffsetDays += (this.calendarView === 'week' ? 7 : 1);
            this.loadCalendarEvents();
        },
        calendarToday() {
            this.calendarOffsetDays = 0;
            this.calendarOffsetMonths = 0;
            this.loadCalendarEvents();
        },
        calendarGoToDate(date) {
            const now = new Date();
            if (this.calendarView === 'month') {
                const target = new Date(date);
                this.calendarOffsetMonths = (target.getMonth() - now.getMonth()) + (target.getFullYear() - now.getFullYear()) * 12;
                this.calendarOffsetDays = 0;
            } else {
                const diff = Math.floor((new Date(date).setHours(0,0,0,0) - now.setHours(0,0,0,0)) / 86400000);
                this.calendarOffsetDays = diff;
                this.calendarOffsetMonths = 0;
            }
            this.loadCalendarEvents();
        },

        calendarRangeLabel() {
            const { start, end } = this._calendarRange();
            if (this.calendarView === 'day') return start.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
            if (this.calendarView === 'week') return `${start.toLocaleDateString([], { month: 'short', day: 'numeric' })} — ${end.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}`;
            if (this.calendarView === 'month') return start.toLocaleDateString([], { month: 'long', year: 'numeric' });
            return `${start.toLocaleDateString([], { month: 'short', day: 'numeric' })} — ${end.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}`;
        },

        calendarMonthDays() {
            const { start, end } = this._calendarRange();
            const days = [];
            const d = new Date(start);
            while (d < end) {
                const dayEvents = this.events.filter(e => {
                    const es = new Date(e.start_time);
                    return es.toDateString() === d.toDateString();
                });
                days.push({ date: new Date(d), events: dayEvents });
                d.setDate(d.getDate() + 1);
            }
            return days;
        },

        calendarDayHours() {
            const hours = [];
            for (let h = 0; h < 24; h++) hours.push({ hour: h, label: `${h}:00` });
            return hours;
        },

        calendarDayEvents() {
            const { start } = this._calendarRange();
            return this.events.filter(e => {
                const es = new Date(e.start_time);
                return es.toDateString() === start.toDateString();
            }).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
        },

        calendarAgendaEvents() {
            return [...this.events].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
        },

        isToday(date) { return date.toDateString() === new Date().toDateString(); },
        isSameMonth(date) { return date.getMonth() === new Date().getMonth() && date.getFullYear() === new Date().getFullYear(); },

        openNewEvent(day, hour = 10) {
            const d = day ? new Date(day.date) : new Date();
            if (!day) d.setHours(hour, 0, 0, 0);
            else d.setHours(hour, 0, 0, 0);
            const end = new Date(d);
            end.setHours(end.getHours() + 1);
            this.eventForm = {
                title: '', description: '', category: 'other',
                start_time: this.toLocalDatetime(d),
                end_time: this.toLocalDatetime(end),
                is_all_day: false, rrule: '',
            };
            this.editingEventId = null;
            this.eventFormOpen = true;
            this.$nextTick(() => document.getElementById('event-title')?.focus());
        },

        editEvent(evt) {
            this.eventForm = {
                title: evt.title, description: evt.description || '', category: evt.category || 'other',
                start_time: this.toLocalDatetime(new Date(evt.start_time)),
                end_time: this.toLocalDatetime(new Date(evt.end_time)),
                is_all_day: evt.is_all_day, rrule: evt.rrule || '',
            };
            this.editingEventId = evt.id;
            this.eventFormOpen = true;
            this.selectedEvent = null;
        },

        viewEvent(evt) {
            this.selectedEvent = evt;
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
                    rrule: this.eventForm.rrule || null,
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
                    if (this.selectedEvent?.id === evtId) this.selectedEvent = null;
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
            const isCustom = providerType === 'custom';
            this.aiForm = {
                id: null,
                provider_type: providerType,
                display_name: isCustom ? '' : providerType.charAt(0).toUpperCase() + providerType.slice(1),
                api_key: '', base_url: providerType === 'ollama' ? 'http://localhost:11434' : '',
                model: '', temperature: 0.7, max_tokens: 1024,
            };
            this.aiFormEdit = false;
            this.aiFormOpen = true;
            this.aiFormError = '';
        },
        editAiConfig(cfg) {
            this.aiForm = {
                id: cfg.id, provider_type: cfg.provider_type, display_name: cfg.display_name,
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
            if (!this.aiForm.display_name.trim()) { this.aiFormError = 'Display name is required'; return; }
            this.aiFormError = '';
            this.aiFormSaving = true;
            try {
                const url = this.aiFormEdit ? `/api/ai/configs/${this.aiForm.id}` : '/api/ai/configs';
                const method = this.aiFormEdit ? 'PUT' : 'POST';
                const payload = { ...this.aiForm };
                if (payload.id) delete payload.id;
                const res = await fetch(url, {
                    method, headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
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
        async activateAiProvider(configId) {
            try {
                const res = await fetch(`/api/ai/configs/${configId}`, {
                    method: 'PUT', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_active: true }),
                });
                if (res.ok) {
                    await this.loadAiConfigs();
                    this.toast('Provider is now active', 'success');
                } else {
                    this.toast('Failed to activate provider', 'error');
                }
            } catch (e) { this.toast('Failed to activate provider', 'error'); }
        },
        async deleteAiConfig(configId) {
            try {
                const res = await fetch(`/api/ai/configs/${configId}`, { method: 'DELETE' });
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

        // AI Organization
        openAiOrganize() {
            this.aiOrganizeOpen = true;
            this.aiOrganizeSuggestions = [];
            this.aiOrganizeApplyAll = [];
        },
        closeAiOrganize() { this.aiOrganizeOpen = false; },
        async aiOrganizeInbox() {
            if (this.aiOrganizeLoading) return;
            this.aiOrganizeLoading = true;
            this.aiOrganizeSuggestions = [];
            try {
                const res = await fetch('/api/ai/organize', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ folder: 'INBOX', limit: 50 }),
                });
                if (res.ok) {
                    const data = await res.json();
                    this.aiOrganizeSuggestions = data.suggestions || [];
                    this.aiOrganizeApplyAll = this.aiOrganizeSuggestions.map(s => s.email_id);
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.toast(err.detail || 'AI organization failed', 'error');
                }
            } catch (e) { this.toast('Network error during AI organization', 'error'); }
            finally { this.aiOrganizeLoading = false; }
        },
        async aiApplySuggestion(emailId, folder) {
            try {
                const res = await fetch(`/api/emails/${emailId}/move`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ folder }),
                });
                if (res.ok) {
                    this.aiOrganizeSuggestions = this.aiOrganizeSuggestions.filter(s => s.email_id !== emailId);
                    this.aiOrganizeApplyAll = this.aiOrganizeApplyAll.filter(id => id !== emailId);
                    this.toast('Email moved', 'success');
                    if (this.currentFolder === 'INBOX') this.loadEmails();
                    this.loadUnreadCount();
                } else {
                    this.toast('Failed to move email', 'error');
                }
            } catch (e) { this.toast('Network error', 'error'); }
        },
        async aiApplyAll() {
            for (const id of this.aiOrganizeApplyAll) {
                const s = this.aiOrganizeSuggestions.find(x => x.email_id === id);
                if (s) await this.aiApplySuggestion(s.email_id, s.suggested_folder);
            }
        },

        // --- Folders ---
        async loadFolders() {
            try {
                const res = await fetch('/api/folders');
                if (res.ok) this.folders = await res.json();
            } catch (e) {}
        },
        openNewFolder() {
            this.folderForm = { name: '', color: 'blue', icon: 'folder' };
            this.folderFormEdit = false;
            this.folderFormEditId = null;
            this.folderFormOpen = true;
            this.$nextTick(() => document.getElementById('folder-name')?.focus());
        },
        editFolder(folder) {
            this.folderForm = { name: folder.name, color: folder.color || 'blue', icon: folder.icon || 'folder' };
            this.folderFormEdit = true;
            this.folderFormEditId = folder.id;
            this.folderFormOpen = true;
        },
        closeFolderForm() {
            this.folderFormOpen = false;
            this.folderFormEdit = false;
            this.folderFormEditId = null;
        },
        async saveFolder() {
            if (this.folderFormSaving) return;
            if (!this.folderForm.name.trim()) { this.toast('Folder needs a name', 'error'); return; }
            this.folderFormSaving = true;
            try {
                const url = this.folderFormEdit ? `/api/folders/${this.folderFormEditId}` : '/api/folders';
                const method = this.folderFormEdit ? 'PUT' : 'POST';
                const res = await fetch(url, {
                    method, headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: this.folderForm.name.trim(),
                        color: this.folderForm.color,
                        icon: this.folderForm.icon,
                    }),
                });
                if (res.ok) {
                    this.closeFolderForm();
                    await this.loadFolders();
                    this.toast(this.folderFormEdit ? 'Folder updated' : 'Folder created', 'success');
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.toast(err.detail || 'Failed to save folder', 'error');
                }
            } catch (e) { this.toast('Network error saving folder', 'error'); }
            finally { this.folderFormSaving = false; }
        },
        async deleteFolder(folderId) {
            try {
                const res = await fetch(`/api/folders/${folderId}`, { method: 'DELETE' });
                if (res.ok) {
                    await this.loadFolders();
                    // If currently viewing the deleted folder, switch to inbox
                    const deleted = this.folders.find(f => f.id === folderId);
                    if (deleted && this.currentFolder === deleted.normalized_name) {
                        this.navigate('inbox');
                    }
                    this.toast('Folder deleted', 'success');
                } else {
                    this.toast('Failed to delete folder', 'error');
                }
            } catch (e) { this.toast('Network error deleting folder', 'error'); }
        },
        async moveEmailToFolder(emailId, folderName) {
            try {
                const res = await fetch(`/api/emails/${emailId}/move`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ folder: folderName }),
                });
                if (res.ok) {
                    this.toast('Email moved', 'success');
                    // Remove from current list if it no longer belongs here
                    const data = await res.json();
                    if (this.currentFolder !== data.folder && this.currentFolder !== 'STARRED') {
                        this.emails = this.emails.filter(e => e.id !== emailId);
                        this.totalEmails = Math.max(0, this.totalEmails - 1);
                    }
                    if (this.selectedEmail?.id === emailId) this.selectedEmail = null;
                    this.loadUnreadCount();
                } else {
                    this.toast('Failed to move email', 'error');
                }
            } catch (e) { this.toast('Network error moving email', 'error'); }
        },
        folderColorClass(color) {
            const map = {
                blue: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200',
                emerald: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200',
                violet: 'bg-violet-100 dark:bg-violet-900/40 text-violet-800 dark:text-violet-200',
                red: 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200',
                amber: 'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200',
                pink: 'bg-pink-100 dark:bg-pink-900/40 text-pink-800 dark:text-pink-200',
                gray: 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200',
                cyan: 'bg-cyan-100 dark:bg-cyan-900/40 text-cyan-800 dark:text-cyan-200',
                indigo: 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200',
                rose: 'bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-200',
            };
            return map[color] || map.blue;
        },
        folderIconSVG(icon) {
            const icons = {
                folder: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>',
                inbox: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/></svg>',
                star: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
                calendar: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>',
                briefcase: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m14 0v10a2 2 0 01-2 2H5a2 2 0 01-2-2V6h18zM8 14v2m8-2v2"/></svg>',
                user: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>',
                tag: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.585l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/></svg>',
                bell: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg>',
                document: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>',
                code: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>',
            };
            return icons[icon] || icons.folder;
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
            const l = { auto_reply: 'Auto-Reply', categorize: 'Categorize', ai_categorize: 'AI Categorize', mark_read: 'Mark Read', star: 'Star', forward: 'Forward' };
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
        formatDateTime(dateStr) {
            if (!dateStr) return '';
            return new Date(dateStr).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        },
        formatDateFull(dateStr) {
            if (!dateStr) return '';
            return new Date(dateStr).toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
        },
        formatTime(dateStr) {
            if (!dateStr) return '';
            return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
        monthYear(d) { return d.toLocaleDateString([], { month: 'long', year: 'numeric' }); },
        weekdayLong(d) { return d.toLocaleDateString([], { weekday: 'long' }); },

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
