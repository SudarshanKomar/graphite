import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Graphite operator-console palette (graphite + signal accents).
        base: "#070A0F",
        surface: "#0C1118",
        panel: "#0F151E",
        elevated: "#131B26",
        line: "#1C2733",
        edge: "#243140",
        ink: "#E6EDF3",
        muted: "#8696A7",
        faint: "#5A6B7B",
        signal: "#33E6B0", // brand teal-green
        "signal-dim": "#1C8F73",
        healthy: "#3FB950",
        critical: "#F85149",
        high: "#F0883E",
        medium: "#D4A72C",
        low: "#58A6FF",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(51,230,176,0.35), 0 0 22px -4px rgba(51,230,176,0.35)",
        "glow-critical": "0 0 0 1px rgba(248,81,73,0.5), 0 0 26px -3px rgba(248,81,73,0.45)",
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 30px -12px rgba(0,0,0,0.6)",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(248,81,73,0.5)" },
          "70%": { boxShadow: "0 0 0 10px rgba(248,81,73,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(248,81,73,0)" },
        },
        "dash": { to: { strokeDashoffset: "-16" } },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "blink": { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.25" } },
      },
      animation: {
        "pulse-ring": "pulse-ring 1.8s cubic-bezier(0.4,0,0.6,1) infinite",
        "dash": "dash 0.7s linear infinite",
        "fade-up": "fade-up 0.25s ease-out",
        "blink": "blink 1.1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
