import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          deep: '#0a0a0f',
          surface: '#12121a',
          elevated: '#1a1a28',
          hover: '#22223a',
        },
        text: {
          primary: '#f0f0f5',
          secondary: '#8888a0',
          muted: '#555570',
        },
        accent: {
          primary: '#6366f1',
          hover: '#818cf8',
        },
        status: {
          success: '#22c55e',
          warning: '#f59e0b',
          error: '#ef4444',
          info: '#3b82f6',
        },
        quality: {
          '4k': '#f59e0b',
          '1080p': '#6366f1',
          '720p': '#8888a0',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'page-title': ['24px', { fontWeight: '700' }],
        'section-header': ['18px', { fontWeight: '600' }],
        'card-title': ['16px', { fontWeight: '600' }],
        'body': ['14px', { fontWeight: '400' }],
        'label': ['13px', { fontWeight: '500' }],
        'caption': ['12px', { fontWeight: '400' }],
        'badge': ['11px', { fontWeight: '600', letterSpacing: '0.5px' }],
      },
      spacing: {
        'xs': '4px',
        'sm': '8px',
        'md': '16px',
        'lg': '24px',
        'xl': '32px',
        '2xl': '48px',
      },
      borderRadius: {
        'sm': '6px',
        'md': '10px',
        'lg': '16px',
        'xl': '20px',
      },
      boxShadow: {
        'sm': '0 1px 3px rgba(0,0,0,0.3)',
        'md': '0 4px 12px rgba(0,0,0,0.4)',
        'lg': '0 8px 24px rgba(0,0,0,0.5)',
        'glow': '0 0 20px rgba(99,102,241,0.15)',
      },
      animation: {
        'shimmer': 'shimmer 2s infinite linear',
        'fade-in': 'fadeIn 150ms ease-out',
        'slide-up': 'slideUp 200ms ease-out',
        'slide-down': 'slideDown 200ms ease-out',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}

export default config
