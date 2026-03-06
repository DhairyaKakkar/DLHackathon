import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#fff0f3",
          100: "#ffe0e7",
          500: "#e8325a",
          600: "#c41f47",
          700: "#a01038",
        },
        fragile: "#dc2626",
        partial: "#b45309",
        durable: "#15803d",
      },
      fontFamily: {
        sans:    ["DM Sans", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
        mono:    ["JetBrains Mono", "Consolas", "monospace"],
      },
      boxShadow: {
        card:       "0 1px 3px rgba(0,0,0,0.07), 0 0 0 1px rgba(0,0,0,0.05)",
        "card-hover": "0 4px 16px rgba(0,0,0,0.10), 0 0 0 1px rgba(0,0,0,0.08)",
        glow:       "0 0 24px rgba(232,50,90,0.18)",
        "glow-sm":  "0 0 12px rgba(232,50,90,0.12)",
        panel:      "0 4px 24px rgba(0,0,0,0.10)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in": {
          from: { opacity: "0", transform: "translateX(-8px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
        "pulse-ring": {
          "0%":      { transform: "scale(0.95)", opacity: "1" },
          "70%, 100%": { transform: "scale(1.1)", opacity: "0" },
        },
      },
      animation: {
        "fade-in":   "fade-in 0.3s ease-out both",
        "slide-in":  "slide-in 0.25s ease-out both",
        "pulse-ring": "pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
