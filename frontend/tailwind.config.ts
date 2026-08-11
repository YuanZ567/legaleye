import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // DESIGN.md 4.1 品牌色（法眼靛蓝）
        brand: {
          50: "#EEF1FD",
          100: "#E0E5FA",
          200: "#C7CEF5",
          400: "#7B89E8",
          500: "#5B6DF0",
          600: "#4055E0",
          700: "#3346C4",
          800: "#2A3A9E",
        },
        // DESIGN.md 4.3 中性色
        ink: {
          900: "#0E1526",
          600: "#475069",
          400: "#8A93A6",
        },
        paper: "#F7F7F5",
        line: {
          100: "#EDF0F5",
          200: "#E3E7EF",
        },
        // DESIGN.md 4.2 语义风险色
        risk: {
          high: "#D92D20",
          highText: "#B42318",
          medium: "#DC6803",
          low: "#1570EF",
          ok: "#12B76A",
          pending: "#98A2B3",
        },
        // shadcn/ui 语义变量（映射 globals.css 的 CSS 变量）
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
      },
      fontFamily: {
        // DESIGN.md 5：IBM Plex 家族 + 中文回退
        sans: [
          '"IBM Plex Sans"',
          "-apple-system",
          '"PingFang SC"',
          '"Microsoft YaHei"',
          '"Noto Sans SC"',
          "sans-serif",
        ],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        xs: "0 1px 2px rgba(14,21,38,.05)",
        sm: "0 2px 6px rgba(14,21,38,.06)",
        lg: "0 12px 32px rgba(14,21,38,.12)",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [animate],
};

export default config;
