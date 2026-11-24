import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0c0c0c",
        panel: "#0f0f0f",
        surface: "#161616",
        "surface-weak": "#1a1a1a",
        "surface-strong": "#242424",
        line: "#2e2e2e",
        "line-strong": "#4b4b4b",
        ink: "#fafafa",
        body: "#aeaeae",
        muted: "#8f8f8f",
        faint: "#6a6a6a",
        accent: "#6b8fff",
        success: "#54d483",
        warning: "#f4b434",
        danger: "#ed5a5a",
      },
      fontFamily: {
        sans: [
          '"Inter Variable"',
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          '"JetBrains Mono Variable"',
          '"JetBrains Mono"',
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      borderRadius: {
        xs: "3px",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.2" },
        },
        "dot-pulse": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        "fade-up": "fade-up 220ms ease-out both",
        blink: "blink 1.1s ease-in-out infinite",
        "dot-pulse": "dot-pulse 2.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
