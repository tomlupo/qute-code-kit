/** @type {import('tailwindcss').Config} */

// Evo Dom Maklerski Brand - Tailwind Configuration
// Copy this into your project's tailwind.config.js or extend from it

module.exports = {
  theme: {
    extend: {
      colors: {
        // Primary palette
        primary: {
          DEFAULT: '#0C2340',
          dark: '#02091A',
          light: '#1F3A5F',
          hover: '#10294F',
        },

        // Accent palette
        accent: {
          DEFAULT: '#2563EB',
          soft: '#DBEAFE',
          hover: '#1D4ED8',
        },

        // Background colors
        background: '#FFFFFF',
        'background-alt': '#F9FAFB',
        surface: '#F1F5F9',

        // Text colors
        foreground: '#0F172A',
        muted: '#6B7280',
        'on-primary': '#FFFFFF',
        'on-accent': '#FFFFFF',

        // Border colors
        border: '#E5E7EB',
        'border-strong': '#CBD5F5',

        // Semantic colors
        error: '#DC2626',
        success: '#16A34A',
        warning: '#D97706',
        info: '#0284C7',
      },

      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'system-ui',
          'sans-serif',
        ],
      },

      fontSize: {
        'h1': ['2.5rem', { lineHeight: '1.1', fontWeight: '700' }],
        'h2': ['2rem', { lineHeight: '1.1', fontWeight: '700' }],
        'h3': ['1.5rem', { lineHeight: '1.25', fontWeight: '600' }],
        'h4': ['1.25rem', { lineHeight: '1.25', fontWeight: '600' }],
        'body': ['1rem', { lineHeight: '1.5', fontWeight: '400' }],
        'small': ['0.875rem', { lineHeight: '1.5', fontWeight: '400' }],
        'xs': ['0.75rem', { lineHeight: '1.5', fontWeight: '400' }],
      },

      fontWeight: {
        regular: '400',
        medium: '500',
        semibold: '600',
        bold: '700',
      },

      spacing: {
        'section': '5rem', // 80px
      },

      borderRadius: {
        'sm': '4px',
        'md': '8px',
        'lg': '16px',
        'xl': '24px',
        'pill': '999px',
      },

      boxShadow: {
        'sm': '0 1px 2px rgba(15, 23, 42, 0.08)',
        'md': '0 4px 12px rgba(15, 23, 42, 0.10)',
        'lg': '0 10px 30px rgba(15, 23, 42, 0.15)',
      },

      maxWidth: {
        'content': '1200px',
      },
    },
  },
  plugins: [],
}
