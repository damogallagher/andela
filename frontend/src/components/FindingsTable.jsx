import { useMemo, useState } from "react";
import styled from "styled-components";

import { SubtleButton } from "./Button.jsx";
import { EmptyText, Eyebrow, Panel, SectionHeader, SectionTitle } from "./Panel.jsx";
import { severityTheme, theme } from "../styles.js";

const FindingsPanel = styled(Panel)`
  grid-column: span 9;
  padding: 24px;

  @media (max-width: 920px) {
    grid-column: 1 / -1;
  }
`;

const Timestamp = styled.span`
  color: #607382;
`;

const FilterToolbar = styled.div`
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(280px, 1.8fr) auto;
  align-items: end;
  gap: 14px;
  margin-bottom: 18px;
  padding: 14px;
  border: 1px solid #e0e8ec;
  border-radius: 8px;
  background: #f8fafb;

  @media (max-width: 920px) {
    grid-template-columns: 1fr;
  }
`;

const FilterState = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-height: 40px;
`;

const ControlLabel = styled.span`
  color: ${theme.colors.muted};
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
`;

const Breadcrumbs = styled.ol`
  display: flex;
  align-items: center;
  gap: 6px;
  list-style: none;
  margin: 0;
  padding: 0;
  color: ${theme.colors.text};
  font-weight: 800;

  li + li::before {
    content: "/";
    margin-right: 6px;
    color: #7a8d9a;
  }
`;

const Field = styled.label`
  display: grid;
  gap: 7px;
`;

const TextInput = styled.input`
  min-height: 40px;
  width: 100%;
  border: 1px solid ${theme.colors.borderStrong};
  border-radius: 6px;
  padding: 8px 10px;
  color: ${theme.colors.text};
  background: #ffffff;
  font-weight: 500;
`;

const Select = styled.select`
  min-height: 40px;
  min-width: 96px;
  border: 1px solid ${theme.colors.borderStrong};
  border-radius: 6px;
  padding: 8px 10px;
  color: ${theme.colors.text};
  background: #ffffff;
  font-weight: 500;
`;

const TableWrap = styled.div`
  overflow-x: auto;
`;

const Table = styled.table`
  width: 100%;
  min-width: 780px;
  border-collapse: collapse;
`;

const Th = styled.th`
  padding: 12px 10px;
  border-bottom: 1px solid #e5ecef;
  color: ${theme.colors.muted};
  font-size: 0.78rem;
  text-align: left;
  text-transform: uppercase;
`;

const Td = styled.td`
  padding: 12px 10px;
  border-bottom: 1px solid #e5ecef;
  color: ${theme.colors.text};
  font-size: 0.92rem;
  text-align: left;
  vertical-align: top;
`;

const Badge = styled.span`
  min-width: 72px;
  border-radius: 999px;
  padding: 4px 9px;
  display: inline-flex;
  justify-content: center;
  color: #ffffff;
  background: ${({ $severity }) => severityTheme[$severity] || theme.colors.muted};
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: capitalize;
`;

const Footer = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;

  @media (max-width: 920px) {
    align-items: stretch;
    flex-direction: column;
  }
`;

const ResultSummary = styled.p`
  margin: 0;
  color: ${theme.colors.muted};
  font-weight: 800;
`;

const Pagination = styled.nav`
  display: flex;
  align-items: center;
  gap: 10px;

  @media (max-width: 920px) {
    justify-content: space-between;
  }
`;

const PageSummary = styled.span`
  min-width: 92px;
  color: ${theme.colors.muted};
  font-size: 0.9rem;
  font-weight: 800;
  text-align: center;
`;

function formatTimestamp(value) {
  if (!value) return "";
  return value.replace("T", " ").slice(0, 19);
}

function labelForSeverity(severity) {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}

function searchableText(finding) {
  return [
    finding.severity,
    finding.title,
    finding.resource,
    finding.file_path,
    finding.recommendation,
    finding.evidence,
  ].join(" ").toLowerCase();
}

export function FindingsTable({ scan, selectedSeverity, onClearSeverity }) {
  const [query, setQuery] = useState("");
  const [pageSize, setPageSize] = useState(5);
  const [page, setPage] = useState(1);
  const findings = useMemo(() => scan?.findings || [], [scan]);

  const filteredFindings = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return findings.filter((finding) => {
      const matchesSeverity = !selectedSeverity || finding.severity === selectedSeverity;
      const matchesQuery = !normalizedQuery || searchableText(finding).includes(normalizedQuery);
      return matchesSeverity && matchesQuery;
    });
  }, [findings, query, selectedSeverity]);

  const pageCount = Math.max(1, Math.ceil(filteredFindings.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * pageSize;
  const visibleFindings = filteredFindings.slice(pageStart, pageStart + pageSize);

  function handleQueryChange(event) {
    setQuery(event.target.value);
    setPage(1);
  }

  function handlePageSizeChange(event) {
    setPageSize(Number(event.target.value));
    setPage(1);
  }

  if (!scan) {
    return (
      <FindingsPanel aria-labelledby="findings-title">
        <SectionHeader>
          <div>
            <Eyebrow>Latest scan</Eyebrow>
            <SectionTitle id="findings-title">Findings</SectionTitle>
          </div>
        </SectionHeader>
        <EmptyText>No findings available yet.</EmptyText>
      </FindingsPanel>
    );
  }

  return (
    <FindingsPanel aria-labelledby="findings-title">
      <SectionHeader>
        <div>
          <Eyebrow>Latest scan</Eyebrow>
          <SectionTitle id="findings-title">Findings</SectionTitle>
        </div>
        <Timestamp>{formatTimestamp(scan.created_at)}</Timestamp>
      </SectionHeader>

      {findings.length > 0 ? (
        <>
          <FilterToolbar aria-label="Finding filters">
            <FilterState>
              <ControlLabel>Showing</ControlLabel>
              <Breadcrumbs aria-label="Current finding filter">
                <li>All severities</li>
                {selectedSeverity ? <li>{labelForSeverity(selectedSeverity)}</li> : null}
              </Breadcrumbs>
              {selectedSeverity ? (
                <SubtleButton type="button" onClick={onClearSeverity}>
                  Clear
                </SubtleButton>
              ) : null}
            </FilterState>
            <Field>
              <ControlLabel>Search findings</ControlLabel>
              <TextInput
                type="search"
                value={query}
                onChange={handleQueryChange}
                placeholder="Search rule, resource, file, or recommendation"
              />
            </Field>
            <Field>
              <ControlLabel>Rows</ControlLabel>
              <Select value={pageSize} onChange={handlePageSizeChange}>
                <option value="5">5</option>
                <option value="10">10</option>
                <option value="25">25</option>
              </Select>
            </Field>
          </FilterToolbar>

          {visibleFindings.length > 0 ? (
            <>
              <TableWrap>
                <Table>
                  <thead>
                    <tr>
                      <Th>Severity</Th>
                      <Th>Rule</Th>
                      <Th>Resource</Th>
                      <Th>File</Th>
                      <Th>Recommendation</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleFindings.map((finding) => (
                      <tr key={finding.id}>
                        <Td><Badge $severity={finding.severity}>{finding.severity}</Badge></Td>
                        <Td>{finding.title}</Td>
                        <Td>{finding.resource}</Td>
                        <Td>{finding.file_path}:{finding.line_number}</Td>
                        <Td>{finding.recommendation}</Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </TableWrap>
              <Footer>
                <ResultSummary>
                  {filteredFindings.length} {filteredFindings.length === 1 ? "matching finding" : "matching findings"}
                </ResultSummary>
                <Pagination aria-label="Findings pagination">
                  <SubtleButton type="button" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>
                    Previous
                  </SubtleButton>
                  <PageSummary>Page {currentPage} of {pageCount}</PageSummary>
                  <SubtleButton type="button" disabled={currentPage >= pageCount} onClick={() => setPage(currentPage + 1)}>
                    Next
                  </SubtleButton>
                </Pagination>
              </Footer>
            </>
          ) : (
            <EmptyText>No findings match the current filters.</EmptyText>
          )}
        </>
      ) : (
        <EmptyText>No findings available yet.</EmptyText>
      )}
    </FindingsPanel>
  );
}
