/** @type {import('tailwindcss').Config} */

// Sonte Brand - Tailwind Configuration
// Palette sourced from sonte.eu / sonte.com
// Copy this into your project's tailwind.config.js or extend from it

module.exports = {
  theme: {
    extend: {
      colors: {
        // Primary palette (Sonte blue)
        primary: {
          DEFAULT: '#53A7DB',
          dark: '#005A99',
          light: '#7FBCE4',
          hover: '#3D95CB',
        },

        // Accent palette (cyan)
        accent: {
          DEFAULT: '#0CB4CE',
          soft: '#CDEFF4',
          hover: '#0998AE',
        },

        // Background colors
        background: '#FFFFFF',
        'background-alt': '#FAFAFA',
        surface: '#F7F7F7',

        // Text colors
        foreground: '#141618',
        muted: '#777777',
        'on-primary': '#FFFFFF',
        'on-accent': '#FFFFFF',

        // Border colors
        border: '#EAEAEA',
        'border-strong': '#DDDDDD',

        // Semantic colors
        error: '#FF3100',
        success: '#28DE72',
        warning: '#FFC42E',
        info: '#0CB4CE',
      },

      fontFamily: {
        sans: [
          'proxima-nova',
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
        'sm': '0 1px 2px rgba(20, 22, 24, 0.06)',
        'md': '0 4px 12px rgba(20, 22, 24, 0.08)',
        'lg': '0 10px 30px rgba(20, 22, 24, 0.12)',
      },

      maxWidth: {
        'content': '1200px',
      },
    },
  },
  plugins: [],
}
