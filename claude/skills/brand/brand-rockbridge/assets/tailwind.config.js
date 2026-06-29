/** @type {import('tailwindcss').Config} */

// Rockbridge TFI Brand - Tailwind Configuration
// Copy this into your project's tailwind.config.js or extend from it

module.exports = {
  theme: {
    extend: {
      colors: {
        // Primary palette (Teal)
        primary: {
          DEFAULT: '#00A19A',
          dark: '#008A84',
          light: '#33B5AF',
          hover: '#008A84',
        },

        // Secondary / Dark palette
        dark: {
          DEFAULT: '#1D3D36',
          light: '#2A5249',
          hover: '#2A5249',
        },
        navy: '#1A2B3C',

        // Accent / Gold palette
        gold: {
          DEFAULT: '#C9A45C',
          light: '#D4B978',
          soft: '#F5EDD8',
          hover: '#D4B978',
        },

        // Background colors
        background: '#FFFFFF',
        'background-alt': '#F5F7F6',
        surface: {
          DEFAULT: '#EEF2F0',
          dark: '#1D3D36',
        },

        // Text colors
        foreground: '#1A1A1A',
        muted: '#6B7280',
        'on-primary': '#FFFFFF',
        'on-dark': '#FFFFFF',
        teal: '#00A19A',

        // Border colors
        border: {
          DEFAULT: '#E5E7EB',
          strong: '#00A19A',
          dark: '#2A5249',
        },

        // Semantic colors
        error: '#DC2626',
        success: '#16A34A',
        warning: '#D97706',
        info: '#00A19A',

        // Chart colors
        chart: {
          primary: '#00A19A',
          secondary: '#1D3D36',
          accent: '#C9A45C',
          positive: '#16A34A',
          negative: '#DC2626',
        },
      },

      fontFamily: {
        sans: [
          'Roboto',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'system-ui',
          'sans-serif',
        ],
        pdf: [
          '"Helvetica Neue"',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
      },

      fontSize: {
        'h1': ['2.5rem', { lineHeight: '1.1', fontWeight: '700' }],
        'h2': ['2rem', { lineHeight: '1.2', fontWeight: '700' }],
        'h3': ['1.5rem', { lineHeight: '1.25', fontWeight: '600' }],
        'h4': ['1.25rem', { lineHeight: '1.3', fontWeight: '600' }],
        'h5': ['1.125rem', { lineHeight: '1.3', fontWeight: '600' }],
        'body': ['1rem', { lineHeight: '1.5', fontWeight: '400' }],
        'small': ['0.875rem', { lineHeight: '1.5', fontWeight: '400' }],
        'xs': ['0.75rem', { lineHeight: '1.5', fontWeight: '400' }],
        'xxs': ['0.625rem', { lineHeight: '1.4', fontWeight: '400' }],
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
        'none': '0',
        'sm': '4px',
        'md': '8px',
        'lg': '16px',
        'xl': '24px',
        'pill': '999px',
      },

      boxShadow: {
        'sm': '0 1px 2px rgba(29, 61, 54, 0.08)',
        'md': '0 4px 12px rgba(29, 61, 54, 0.12)',
        'lg': '0 10px 30px rgba(29, 61, 54, 0.16)',
      },

      maxWidth: {
        'content': '1200px',
      },
    },
  },
  plugins: [],
}
