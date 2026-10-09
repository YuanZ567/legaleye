import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 品牌色（M10+ 主题改版：公文卷宗风 —— 朱砂印章红，替代原靛蓝）
        brand: {
          50: "#FBF1EE",
          100: "#F5DDD5",
          200: "#E9C0B3",
          400: "#C4704F",
          500: "#A9502F",
          600: "#9E3423",
          700: "#7F2A1C",
          800: "#64221A",
        },
        // 中性色（暖调墨色，替代冷蓝灰）
        ink: {
          900: "#1C1917",
          600: "#57534E",
          400: "#A29A8E",
        },
        paper: "#F7F5F0",
        line: {
          100: "#EBE6DC",
          200: "#DFD9CD",
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
        // 展示字：思源宋体（法律文书感），回退本机宋体
        display: [
          '"Noto Serif SC"',
          '"Songti SC"',
          '"SimSun"',
          "serif",
        ],
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
        xs: "0 1px 2px rgba(28,25,23,.05)",
        sm: "0 2px 6px rgba(28,25,23,.06)",
        lg: "0 12px 32px rgba(28,25,23,.12)",
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
