import styled from "styled-components";

import { EmptyText, Eyebrow, Panel, SectionHeader, SectionTitle } from "./Panel.jsx";
import { formatScanDateTime } from "../time.js";
import { severityTheme, theme } from "../styles.js";

const ComparisonPanel = styled(Panel)`
  grid-column: span 6;
  min-width: 0;
  padding: 24px;

  @media (max-width: 1120px) {
    grid-column: 1 / -1;
  }
`;

const CompareControls = styled.div`
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;

  @media (max-width: 720px) {
    grid-template-columns: 1fr;
  }
`;

const Field = styled.label`
  display: grid;
  gap: 7px;
  color: ${theme.colors.muted};
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
`;

const Select = styled.select`
  min-height: 40px;
  width: 100%;
  border: 1px solid ${theme.colors.borderStrong};
  border-radius: 6px;
  padding: 8px 10px;
  color: ${theme.colors.text};
  background: #ffffff;
  font-weight: 600;
`;

const Summary = styled.p`
  margin: 0 0 14px;
  border: 1px solid ${({ $regression }) => ($regression ? "#efb3a3" : "#cce5dd")};
  border-radius: 8px;
  padding: 12px 14px;
  color: ${({ $regression }) => ($regression ? "#7f1d1d" : "#0f4f46")};
  background: ${({ $regression }) => ($regression ? "#fff1ed" : "#edf8f4")};
  font-weight: 900;
`;

const Metrics = styled.dl`
  margin: 0 0 16px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;

  @media (max-width: 720px) {
    grid-template-columns: 1fr;
  }

  div {
    border: 1px solid #e1e9ed;
    border-radius: 8px;
    padding: 12px;
    background: #f8fafb;
  }

  dt {
    color: ${theme.colors.muted};
    font-size: 0.74rem;
    font-weight: 800;
    text-transform: uppercase;
  }

  dd {
    margin: 4px 0 0;
    color: ${theme.colors.text};
    font-size: 1.4rem;
    font-weight: 900;
  }
`;

const DeltaList = styled.ul`
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;

  @media (max-width: 720px) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
`;

const DeltaItem = styled.li`
  border-top: 4px solid ${({ $severity }) => severityTheme[$severity] || theme.colors.muted};
  border-radius: 8px;
  padding: 10px;
  background: #f8fafb;
  color: ${theme.colors.text};
  font-weight: 900;
  text-transform: capitalize;
`;

const DeltaValue = styled.span`
  display: block;
  margin-top: 4px;
  color: ${({ $severity }) => severityTheme[$severity] || theme.colors.muted};
  font-size: 1.25rem;
`;

const FindingList = styled.ul`
  margin: 0;
  padding-left: 18px;
  color: ${theme.colors.text};
`;

const FindingItem = styled.li`
  margin-bottom: 8px;
`;

const Timestamp = styled.span`
  color: ${theme.colors.muted};
  font-size: 0.9rem;
  font-weight: 800;
`;

function scanOptionLabel(scan) {
  return `${scan.label} - ${scan.risk_score}% - ${formatScanDateTime(scan.created_at)}`;
}

function signed(value) {
  return value > 0 ? `+${value}` : String(value);
}

function selectValue(value) {
  return value ? String(value) : "";
}

export function ScanComparison({
  scans,
  baseScanId,
  headScanId,
  onBaseChange,
  onHeadChange,
  comparison,
  loading,
  error,
}) {
  return (
    <ComparisonPanel aria-labelledby="comparison-title">
      <SectionHeader>
        <div>
          <Eyebrow>Scan comparison</Eyebrow>
          <SectionTitle id="comparison-title">Regression Detection</SectionTitle>
        </div>
        {comparison?.head_scan ? <Timestamp>{formatScanDateTime(comparison.head_scan.created_at)}</Timestamp> : null}
      </SectionHeader>

      {scans.length > 1 ? (
        <>
          <CompareControls>
            <Field>
              <span>Baseline scan</span>
              <Select value={selectValue(baseScanId)} onChange={(event) => onBaseChange(Number(event.target.value))}>
                {scans.map((scan) => (
                  <option key={scan.id} value={scan.id} disabled={scan.id === headScanId}>
                    {scanOptionLabel(scan)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field>
              <span>Candidate scan</span>
              <Select value={selectValue(headScanId)} onChange={(event) => onHeadChange(Number(event.target.value))}>
                {scans.map((scan) => (
                  <option key={scan.id} value={scan.id} disabled={scan.id === baseScanId}>
                    {scanOptionLabel(scan)}
                  </option>
                ))}
              </Select>
            </Field>
          </CompareControls>

          {loading ? <EmptyText>Comparing scans...</EmptyText> : null}
          {error ? <EmptyText>{error}</EmptyText> : null}
          {comparison && !loading ? (
            <>
              <Summary $regression={comparison.new_findings_count > 0}>
                {comparison.regression_summary}
              </Summary>
              <Metrics>
                <div>
                  <dt>Risk score</dt>
                  <dd>{signed(comparison.risk_score_delta)}</dd>
                </div>
                <div>
                  <dt>New findings</dt>
                  <dd>{comparison.new_findings_count}</dd>
                </div>
                <div>
                  <dt>Resolved</dt>
                  <dd>{comparison.resolved_findings_count}</dd>
                </div>
              </Metrics>
              <DeltaList aria-label="Severity deltas">
                {comparison.severity_deltas.map((delta) => (
                  <DeltaItem key={delta.severity} $severity={delta.severity}>
                    {delta.severity}
                    <DeltaValue $severity={delta.severity}>{signed(delta.new - delta.resolved)}</DeltaValue>
                  </DeltaItem>
                ))}
              </DeltaList>
              {comparison.new_findings.length > 0 ? (
                <FindingList aria-label="New findings">
                  {comparison.new_findings.slice(0, 4).map((finding) => (
                    <FindingItem key={finding.id}>
                      {finding.severity} - {finding.title} - {finding.resource}
                    </FindingItem>
                  ))}
                </FindingList>
              ) : null}
            </>
          ) : null}
        </>
      ) : (
        <EmptyText>At least two scans are needed to compare changes.</EmptyText>
      )}
    </ComparisonPanel>
  );
}
