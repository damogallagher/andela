import { createGlobalStyle } from "styled-components";

export const theme = {
  colors: {
    background: "#f5f7f8",
    panel: "#ffffff",
    border: "#dce4e8",
    borderStrong: "#c9d6dc",
    text: "#18212f",
    muted: "#526879",
    teal: "#0f766e",
    tealSoft: "#e6f3f1",
    scoreGreen: "#15803d",
    scoreAmber: "#b7791f",
    scoreRed: "#b91c1c",
    critical: "#b91c1c",
    high: "#c2410c",
    medium: "#b7791f",
    low: "#0f766e",
  },
  shadow: "0 8px 24px rgba(33, 48, 66, 0.06)",
};

export const severityTheme = {
  critical: theme.colors.critical,
  high: theme.colors.high,
  medium: theme.colors.medium,
  low: theme.colors.low,
};

export const GlobalStyle = createGlobalStyle`
  :root {
    color-scheme: light;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: ${theme.colors.background};
    color: ${theme.colors.text};
  }

  * {
    box-sizing: border-box;
  }

  [hidden] {
    display: none !important;
  }

  body {
    margin: 0;
    min-height: 100vh;
    background: ${theme.colors.background};
  }

  button,
  input,
  select {
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
`;
