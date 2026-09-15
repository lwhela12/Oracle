/* Explicit anonymous events only. No autocapture, replay, or reading content. */
window.OracleAnalytics = (() => {
    const visitorKey = 'oracle_anonymous_visitor';
    const optOutKey = 'oracle_analytics_opt_out';
    let visitorId = null;
    let active = false;
    const uuid = () => window.crypto?.randomUUID?.() || null;
    function optedOut() {
        try {
            return navigator.doNotTrack === '1' || navigator.globalPrivacyControl === true || localStorage.getItem(optOutKey) === '1';
        } catch (_) { return true; }
    }
    async function initialize() {
        if (optedOut()) return;
        try {
            const response = await fetch('/analytics/config', {signal: AbortSignal.timeout(1500)});
            if (!response.ok || !(await response.json()).enabled || optedOut()) return;
            visitorId = localStorage.getItem(visitorKey);
            if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(visitorId || '')) {
                visitorId = uuid();
                if (!visitorId) return;
                localStorage.setItem(visitorKey, visitorId);
            }
            active = true;
            await fetch('/analytics/visit', {method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({visitor_id: visitorId}), signal: AbortSignal.timeout(2500)});
        } catch (_) { /* Analytics failures never block the reading interface. */ }
    }
    function readingContext() {
        return {visitor_id: active && !optedOut() ? visitorId : null,
                reading_id: uuid(), analytics_opt_out: optedOut()};
    }
    function toggle(button) {
        try {
            const disabled = localStorage.getItem(optOutKey) !== '1';
            localStorage.setItem(optOutKey, disabled ? '1' : '0');
            if (disabled) {
                localStorage.removeItem(visitorKey);
                active = false;
                visitorId = null;
            } else { initialize(); }
            if (button) button.textContent = disabled ? 'Usage analytics off — enable' : 'Usage analytics on — disable';
        } catch (_) {
            if (button) button.textContent = 'Usage analytics unavailable in this browser';
        }
    }
    initialize();
    return {readingContext, toggle};
})();
