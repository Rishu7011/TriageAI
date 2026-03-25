/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg:       '#0D1117',
        card:     '#161B22',
        border:   '#30363D',
        danger:   '#E63946',
        warning:  '#FF8C00',
        watch:    '#FFD700',
        stable:   '#4CAF50',
        primary:  '#E6EDF3',
        muted:    '#8B949E',
      },
    },
  },
  plugins: [],
}
