/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      animation: {
        'slide-in-top': 'slideInTop 0.5s cubic-bezier(0.250, 0.460, 0.450, 0.940) both',
        'fade-out': 'fadeOut 0.5s ease-out both',
      },
      keyframes: {
        slideInTop: {
          '0%': { transform: 'translateY(-50px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0', display: 'none' },
        }
      }
    },
  },
  plugins: [],
}
