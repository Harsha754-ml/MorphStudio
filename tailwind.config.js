/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      colors: {
        base: '#0d0d0d',
        surface: '#161616',
        raised: '#1e1e1e',
        overlay: '#242424',
        panel: '#141414',
        accent: '#00d2ff',
        'accent-dim': 'rgba(0,210,255,0.12)',
      }
    }
  },
  plugins: []
}
