(() => {
    const storageKey = 'lindholmen-lunch-theme';
    let savedTheme;
    try {
        savedTheme = localStorage.getItem(storageKey);
    } catch (_) {
        // The toggle still works when browser storage is unavailable.
    }
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme === 'light' || savedTheme === 'dark'
        ? savedTheme : (prefersDark ? 'dark' : 'light');

    // Run in the head before the page is painted, including on weekday changes.
    document.documentElement.dataset.theme = theme;
    document.addEventListener('DOMContentLoaded', () => {
        const toggle = document.getElementById('theme-toggle');
        if (!toggle) return;
        const updateToggle = () => {
            toggle.setAttribute('aria-pressed', String(document.documentElement.dataset.theme === 'dark'));
        };
        updateToggle();
        toggle.hidden = false;
        toggle.addEventListener('click', () => {
            const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
            document.documentElement.dataset.theme = next;
            updateToggle();
            try {
                localStorage.setItem(storageKey, next);
            } catch (_) {
                // Keep the selected theme for this page even if it cannot be saved.
            }
        });
    });
})();
