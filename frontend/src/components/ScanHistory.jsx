import styled from "styled-components";

import { EmptyText, Eyebrow, Panel, SectionHeader, SectionTitle } from "./Panel.jsx";
import { theme } from "../styles.js";

const HistoryPanel = styled(Panel)`
  grid-column: span 3;
  padding: 24px;

  @media (max-width: 920px) {
    grid-column: 1 / -1;
  }
`;

const HistoryList = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
`;

const HistoryItem = styled.li`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e5ecef;
`;

const Label = styled.span`
  min-width: 0;
  color: ${theme.colors.text};
`;

const Score = styled.strong`
  color: ${theme.colors.teal};
`;

export function ScanHistory({ scans }) {
  return (
    <HistoryPanel aria-labelledby="history-title">
      <SectionHeader>
        <div>
          <Eyebrow>Postgres-backed audit trail</Eyebrow>
          <SectionTitle id="history-title">Recent Scans</SectionTitle>
        </div>
      </SectionHeader>
      {scans.length > 0 ? (
        <HistoryList>
          {scans.slice(0, 8).map((scan) => (
            <HistoryItem key={scan.id}>
              <Label>{scan.label}</Label>
              <Score>{scan.risk_score}</Score>
            </HistoryItem>
          ))}
        </HistoryList>
      ) : (
        <EmptyText>No scan history yet.</EmptyText>
      )}
    </HistoryPanel>
  );
}
