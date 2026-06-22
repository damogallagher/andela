import styled from "styled-components";

import { Panel } from "./Panel.jsx";
import { severityTheme, theme } from "../styles.js";

const Metrics = styled.section`
  grid-column: span 7;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;

  @media (max-width: 920px) {
    grid-column: 1 / -1;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
  }
`;

const SeverityButton = styled(Panel).attrs({ as: "button" })`
  --severity-color: ${({ $severity }) => severityTheme[$severity] || theme.colors.muted};
  min-height: 180px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start;
  border-top: 5px solid var(--severity-color);
  color: ${theme.colors.text};
  text-align: left;

  &:hover,
  &:focus-visible,
  &[aria-pressed="true"] {
    border-color: var(--severity-color);
    box-shadow: 0 10px 26px rgba(33, 48, 66, 0.12);
  }

  &[aria-pressed="true"] {
    background: color-mix(in srgb, var(--severity-color) 9%, #ffffff);
  }
`;

const Label = styled.span`
  color: ${theme.colors.muted};
  font-weight: 800;
`;

const Count = styled.strong`
  color: var(--severity-color);
  font-size: 3rem;
  line-height: 1;
`;

const severities = ["critical", "high", "medium", "low"];

export function SeverityCards({ counts, selectedSeverity, onSelect }) {
  return (
    <Metrics aria-label="Finding counts by severity">
      {severities.map((severity) => (
        <SeverityButton
          key={severity}
          type="button"
          $severity={severity}
          aria-pressed={selectedSeverity === severity}
          onClick={() => onSelect(selectedSeverity === severity ? null : severity)}
        >
          <Label>{severity[0].toUpperCase() + severity.slice(1)}</Label>
          <Count>{counts[severity] || 0}</Count>
        </SeverityButton>
      ))}
    </Metrics>
  );
}
