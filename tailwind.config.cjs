// tailwind.config.cjs
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#1E40AF",
        secondary: "#059669",
        accent: "#D97706",
        critical: "#DC2626",
        neutral: "#6B7280",
      },
    },
  },
  plugins: [],
};
