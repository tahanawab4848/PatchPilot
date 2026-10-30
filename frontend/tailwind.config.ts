import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Modern engineering dark palette
        surface: {
          DEFAULT: "#0b0f17",
          1: "#111722",
          2: "#182030",
          3: "#1f2a3f",
          card: "#121826",
        },
        border: {
          DEFAULT: "#232e42",
          subtle: "#1a2232",
          accent: "rgba(0, 188, 212, 0.3)",
        },
        accent: {
          DEFAULT: "#00bcd4",
          muted: "#087383",
          bright: "#22d3ee",
          glow: "rgba(0, 188, 212, 0.15)",
        },
        status: {
          success: "#34d399",
          warning: "#fbbf24",
          error: "#f87171",
          info: "#60a5fa",
          neutral: "#94a3b8",
        },
        text: {
          primary: "#f1f5f9",
          secondary: "#94a3b8",
          muted: "#64748b",
          link: "#38bdf8",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      boxShadow: {
        "glow-sm": "0 0 15px -3px rgba(0, 188, 212, 0.2)",
        "glow-md": "0 0 25px -4px rgba(0, 188, 212, 0.25)",
        "glow-lg": "0 0 40px -5px rgba(0, 188, 212, 0.35)",
        "glow-success": "0 0 20px -4px rgba(52, 211, 153, 0.3)",
        "inner-glow": "inset 0 1px 0 0 rgba(255, 255, 255, 0.05)",
      },
      borderRadius: {
        xl: "0.75rem",
        lg: "0.5rem",
        md: "0.375rem",
        sm: "0.25rem",
      },
      animation: {
        "fade-in": "fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in": "slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        "pulse-subtle": "pulseSubtle 2.5s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%": { transform: "translateY(-8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        pulseSubtle: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
