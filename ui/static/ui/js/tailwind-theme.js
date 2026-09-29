/**
 * ForensiQ Centralized Tailwind Theme Configuration
 * Primary Brand Base: Violet (#502D55)
 */

window.tailwind = window.tailwind || {};
window.tailwind.config = {
    darkMode: 'class',
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
                aptos: ['Aptos', 'Aptos Display', 'Segoe UI', 'system-ui', 'sans-serif'],
            },
            colors: {
                zinc: {
                    800: '#351c3a',
                    850: '#2b1630',
                    900: '#201024',
                    950: '#140a17',
                },
                violet: {
                    brand: '#502D55',
                    50: '#faf5fb',
                    100: '#f4ecf5',
                    200: '#e4d5e6',
                    300: '#cdb3d0',
                    400: '#ba88bf',
                    500: '#96579c',
                    600: '#773e7c',
                    700: '#502D55',
                    800: '#3d2241',
                    900: '#2c1830',
                    950: '#140a17',
                },
                amber: {
                    450: '#f59e0b',
                    500: '#f59e0b',
                    550: '#d97706',
                }
            }
        }
    }
};
