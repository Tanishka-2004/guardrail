/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: "var(--bg-app)",
        surface: {
          DEFAULT: "var(--bg-surface)",
          elevated: "var(--bg-surface-elevated)",
          subtle: "var(--bg-surface-subtle)",
          border: "var(--border-surface)",
        },
        brand: {
          50: "var(--brand-light)",
          100: "var(--brand-border)",
          500: "var(--brand-color)",
          600: "var(--brand-color)",
          700: "var(--brand-hover)",
        },
        risk: {
          critical: "#F43F5E",
          high: "#F97316",
          medium: "#EAB308",
          low: "#06B6D4",
        },
        status: {
          healthy: "#10B981",
          warning: "#F59E0B",
          breached: "#EF4444",
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
