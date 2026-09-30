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
                // Semantic Dynamic Theme Aliases (Powered by CSS Variables)
                theme: {
                    app: 'var(--fq-bg-app)',
                    surface: 'var(--fq-bg-surface)',
                    elevated: 'var(--fq-bg-surface-elevated)',
                    subtle: 'var(--fq-bg-subtle)',
                    border: 'var(--fq-border-subtle)',
                    'border-strong': 'var(--fq-border-strong)',
                    text: 'var(--fq-text-main)',
                    muted: 'var(--fq-text-muted)',
                    subtle_text: 'var(--fq-text-subtle)',
                    brand: 'var(--fq-brand-violet)',
                },
                zinc: {
                    800: '#351c3a',
                    850: '#2b1630',
                    900: '#201024',
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
