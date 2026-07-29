import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#061324",
          900: "#0A1E35",
          800: "#102B4A",
          700: "#163B63"
        },
        ink: "#172033",
        mist: "#F4F7FB",
        line: "#D9E2EC",
        success: "#0E9F6E",
        warning: "#B7791F",
        danger: "#C2410C"
      },
      boxShadow: {
        soft: "0 16px 40px rgba(15, 23, 42, 0.08)"
      }
    }
  },
  plugins: []
} satisfies Config;
