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
          50: "#1e1b4b",
          100: "#312e81",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
        },
        fragile: "#f43f5e",
        partial: "#f59e0b",
        durable: "#10b981",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Space Grotesk", "Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.06)",
        "card-hover":
          "0 4px 24px rgba(99,102,241,0.12), 0 0 0 1px rgba(255,255,255,0.1)",
        glow: "0 0 24px rgba(99,102,241,0.3)",
        "glow-sm": "0 0 12px rgba(99,102,241,0.2)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in": {
          from: { opacity: "0", transform: "translateX(-8px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.95)", opacity: "1" },
          "70%, 100%": { transform: "scale(1.1)", opacity: "0" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.3s ease-out both",
        "slide-in": "slide-in 0.25s ease-out both",
        "pulse-ring": "pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
