/**
 * ForensiQ Theme Manager
 * Handles FOUC prevention, localStorage synchronization, and dark/light mode toggles.
 */

(function () {
    // 1. Immediate FOUC Prevention (Runs synchronously in <head>)
    const storedTheme = localStorage.getItem('color-theme');
    const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;

    if (storedTheme === 'light' || (!storedTheme && prefersLight)) {
        document.documentElement.classList.remove('dark');
    } else {
        document.documentElement.classList.add('dark');
    }

    // 2. Global Theme Helper API
    window.ForensiQTheme = {
        isDark: function () {
            return document.documentElement.classList.contains('dark');
        },
        setTheme: function (theme) {
            const isDark = theme === 'dark';
            if (isDark) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
            localStorage.setItem('color-theme', theme);
            this.updateIcons();
            window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark } }));
        },
        toggleTheme: function () {
            const isDark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('color-theme', isDark ? 'dark' : 'light');
            this.updateIcons();
            window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark } }));
            return isDark;
        },
        updateIcons: function () {
            const darkIcon = document.getElementById('theme-toggle-dark-icon');
            const lightIcon = document.getElementById('theme-toggle-light-icon');
            const isDark = this.isDark();

            if (darkIcon && lightIcon) {
                if (isDark) {
                    lightIcon.classList.remove('hidden');
                    darkIcon.classList.add('hidden');
                } else {
                    darkIcon.classList.remove('hidden');
                    lightIcon.classList.add('hidden');
                }
            }
        }
    };

    // 3. Attach Event Listeners on DOM Ready
    document.addEventListener('DOMContentLoaded', function () {
        window.ForensiQTheme.updateIcons();

        const themeToggleBtn = document.getElementById('theme-toggle');
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', function () {
                window.ForensiQTheme.toggleTheme();
            });
        }
    });
})();
