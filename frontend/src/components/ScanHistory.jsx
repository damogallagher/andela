import styled from "styled-components";

import { EmptyText, Eyebrow, Panel, SectionHeader, SectionTitle } from "./Panel.jsx";
import { formatScanDateTime } from "../time.js";
import { theme } from "../styles.js";

const HistoryPanel = styled(Panel)`
  grid-column: 1 / -1;
  padding: 24px;
`;

const HistoryList = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
`;

const HistoryItem = styled.li`
  padding-bottom: 10px;
  border-bottom: 1px solid #e5ecef;
`;

const HistoryButton = styled.button`
  width: 100%;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 8px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 12px;
  color: ${theme.colors.text};
  background: transparent;
  text-align: left;

  &:hover,
  &:focus-visible,
  &[aria-pressed="true"] {
    border-color: ${theme.colors.borderStrong};
    background: ${theme.colors.tealSoft};
  }
`;

const Label = styled.span`
  min-width: 0;
  color: ${theme.colors.text};
`;

const Timestamp = styled.span`
  grid-column: 1 / -1;
  color: ${theme.colors.muted};
  font-size: 0.82rem;
  font-weight: 700;
`;

const Score = styled.strong`
  color: ${theme.colors.teal};
`;

export function ScanHistory({ scans, selectedScanId, onSelectScan }) {
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
              <HistoryButton
                type="button"
                aria-pressed={selectedScanId === scan.id}
                onClick={() => onSelectScan(scan.id)}
              >
                <Label>{scan.label}</Label>
                <Score>{scan.risk_score}</Score>
                <Timestamp>{formatScanDateTime(scan.created_at)}</Timestamp>
              </HistoryButton>
            </HistoryItem>
          ))}
        </HistoryList>
      ) : (
        <EmptyText>No scan history yet.</EmptyText>
      )}
    </HistoryPanel>
  );
}
