import { useMemo, useState } from "react";
import styled from "styled-components";

import { SubtleButton } from "./Button.jsx";
import { EmptyText, Eyebrow, Panel, SectionHeader, SectionTitle } from "./Panel.jsx";
import { formatScanDateTime } from "../time.js";
import { severityTheme, theme } from "../styles.js";

const FindingsPanel = styled(Panel)`
  grid-column: span 9;
  min-width: 0;
  padding: 24px;

  @media (max-width: 1120px) {
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
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid #e5ecef;
  border-radius: 8px;
  background: #ffffff;
`;

const Table = styled.table`
  width: 100%;
  min-width: 1180px;
  border-collapse: collapse;
  table-layout: fixed;
`;

const Th = styled.th`
  padding: 0;
  border-bottom: 1px solid #e5ecef;
  color: ${theme.colors.muted};
  font-size: 0.78rem;
  text-align: left;
  text-transform: uppercase;
`;

const SortButton = styled.button`
  width: 100%;
  min-height: 44px;
  border: 0;
  padding: 12px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: inherit;
  background: transparent;
  font-weight: 800;
  text-align: left;
  text-transform: uppercase;

  &:hover,
  &:focus-visible {
    background: ${theme.colors.tealSoft};
    color: ${theme.colors.text};
  }
`;

const SortIndicator = styled.span`
  flex: 0 0 auto;
  min-width: 34px;
  color: ${({ $active }) => ($active ? theme.colors.teal : theme.colors.muted)};
  font-size: 0.7rem;
  font-weight: 900;
  text-align: right;
`;

const Td = styled.td`
  padding: 12px 10px;
  border-bottom: 1px solid #e5ecef;
  color: ${theme.colors.text};
  font-size: 0.92rem;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
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

const columns = [
  { key: "severity", label: "Severity", width: "130px" },
  { key: "title", label: "Rule", width: "190px" },
  { key: "resource", label: "Resource", width: "290px" },
  { key: "file", label: "File", width: "240px" },
  { key: "recommendation", label: "Recommendation", width: "330px" },
];

const severityRank = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function sortValue(finding, key) {
  if (key === "severity") {
    return severityRank[finding.severity] ?? 99;
  }
  if (key === "file") {
    return `${finding.file_path || ""}:${finding.line_number || ""}`.toLowerCase();
  }
  return String(finding[key] || "").toLowerCase();
}

function sortFindings(findings, sort) {
  if (!sort) {
    return findings;
  }
  return [...findings].sort((left, right) => {
    const leftValue = sortValue(left, sort.key);
    const rightValue = sortValue(right, sort.key);
    const base = typeof leftValue === "number" && typeof rightValue === "number"
      ? leftValue - rightValue
      : String(leftValue).localeCompare(String(rightValue), undefined, { numeric: true, sensitivity: "base" });
    return sort.direction === "asc" ? base : -base;
  });
}

function ariaSort(columnKey, sort) {
  if (sort?.key !== columnKey) {
    return "none";
  }
  return sort.direction === "asc" ? "ascending" : "descending";
}

export function FindingsTable({ scan, selectedSeverity, onClearSeverity }) {
  const [query, setQuery] = useState("");
  const [pageSize, setPageSize] = useState(5);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState(null);
  const findings = useMemo(() => scan?.findings || [], [scan]);

  const filteredFindings = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return findings.filter((finding) => {
      const matchesSeverity = !selectedSeverity || finding.severity === selectedSeverity;
      const matchesQuery = !normalizedQuery || searchableText(finding).includes(normalizedQuery);
      return matchesSeverity && matchesQuery;
    });
  }, [findings, query, selectedSeverity]);

  const sortedFindings = useMemo(() => sortFindings(filteredFindings, sort), [filteredFindings, sort]);
  const pageCount = Math.max(1, Math.ceil(sortedFindings.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * pageSize;
  const visibleFindings = sortedFindings.slice(pageStart, pageStart + pageSize);

  function handleQueryChange(event) {
    setQuery(event.target.value);
    setPage(1);
  }

  function handlePageSizeChange(event) {
    setPageSize(Number(event.target.value));
    setPage(1);
  }

  function handleSort(columnKey) {
    setSort((current) => {
      if (current?.key === columnKey) {
        return { key: columnKey, direction: current.direction === "asc" ? "desc" : "asc" };
      }
      return { key: columnKey, direction: "asc" };
    });
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
        <Timestamp>{formatScanDateTime(scan.created_at)}</Timestamp>
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
              <TableWrap role="region" aria-label="Scrollable findings table" tabIndex="0">
                <Table>
                  <colgroup>
                    {columns.map((column) => (
                      <col key={column.key} style={{ width: column.width }} />
                    ))}
                  </colgroup>
                  <thead>
                    <tr>
                      {columns.map((column) => (
                        <Th key={column.key} aria-sort={ariaSort(column.key, sort)}>
                          <SortButton type="button" aria-label={`Sort by ${column.label}`} onClick={() => handleSort(column.key)}>
                            <span>{column.label}</span>
                            <SortIndicator $active={sort?.key === column.key}>
                              {sort?.key === column.key ? (sort.direction === "asc" ? "A-Z" : "Z-A") : "Sort"}
                            </SortIndicator>
                          </SortButton>
                        </Th>
                      ))}
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
