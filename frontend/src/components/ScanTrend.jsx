import styled from "styled-components";

import { EmptyText, Eyebrow, Panel, SectionHeader, SectionTitle } from "./Panel.jsx";
import { formatScanDateTime } from "../time.js";
import { theme } from "../styles.js";

const TrendPanel = styled(Panel)`
  grid-column: span 6;
  min-width: 0;
  padding: 24px;

  @media (max-width: 1120px) {
    grid-column: 1 / -1;
  }
`;

const ChartWrap = styled.div`
  height: 180px;
  border: 1px solid #e1e9ed;
  border-radius: 8px;
  padding: 12px;
  background: #f8fafb;
`;

const Chart = styled.svg`
  width: 100%;
  height: 100%;
  display: block;
`;

const TrendLine = styled.polyline`
  fill: none;
  stroke: ${theme.colors.teal};
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
`;

const Point = styled.circle`
  fill: ${({ $active }) => ($active ? theme.colors.scoreRed : "#ffffff")};
  stroke: ${({ $active }) => ($active ? theme.colors.scoreRed : theme.colors.teal)};
  stroke-width: 2.5;
`;

const AxisLabel = styled.text`
  fill: ${theme.colors.muted};
  font-size: 7px;
  font-weight: 800;
`;

const TrendStats = styled.dl`
  margin: 14px 0 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }

  div {
    min-width: 0;
  }

  dt {
    color: ${theme.colors.muted};
    font-size: 0.78rem;
    font-weight: 800;
    text-transform: uppercase;
  }

  dd {
    margin: 4px 0 0;
    color: ${theme.colors.text};
    font-size: 1.35rem;
    font-weight: 900;
  }
`;

const Timestamp = styled.span`
  color: ${theme.colors.muted};
  font-size: 0.9rem;
  font-weight: 800;
`;

function trendScans(scans) {
  return [...scans]
    .sort((left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime())
    .slice(-10);
}

function pointsFor(scans) {
  if (scans.length === 1) {
    return [{ x: 50, y: 60, scan: scans[0] }];
  }
  return scans.map((scan, index) => {
    const x = 8 + (index * 84) / (scans.length - 1);
    const y = 10 + ((100 - scan.risk_score) * 44) / 100;
    return { x, y, scan };
  });
}

export function ScanTrend({ scans, selectedScanId }) {
  const orderedScans = trendScans(scans);
  const points = pointsFor(orderedScans);
  const first = orderedScans[0] || null;
  const latest = orderedScans[orderedScans.length - 1] || null;
  const change = first && latest ? latest.risk_score - first.risk_score : 0;
  const pointString = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <TrendPanel aria-labelledby="trend-title">
      <SectionHeader>
        <div>
          <Eyebrow>Risk score over time</Eyebrow>
          <SectionTitle id="trend-title">Risk Score Trend</SectionTitle>
        </div>
        {latest ? <Timestamp>{formatScanDateTime(latest.created_at)}</Timestamp> : null}
      </SectionHeader>

      {orderedScans.length > 1 ? (
        <>
          <ChartWrap>
            <Chart viewBox="0 0 100 64" role="img" aria-label={`Risk score trend across ${orderedScans.length} scans`}>
              <title>Risk score trend across {orderedScans.length} scans</title>
              <line x1="8" y1="10" x2="8" y2="54" stroke="#d8e3e8" strokeWidth="0.8" />
              <line x1="8" y1="54" x2="92" y2="54" stroke="#d8e3e8" strokeWidth="0.8" />
              <AxisLabel x="1" y="13">100</AxisLabel>
              <AxisLabel x="3" y="55">0</AxisLabel>
              <TrendLine points={pointString} vectorEffect="non-scaling-stroke" />
              {points.map((point) => (
                <Point
                  key={point.scan.id}
                  cx={point.x}
                  cy={point.y}
                  r={point.scan.id === selectedScanId ? 3.6 : 2.8}
                  $active={point.scan.id === selectedScanId}
                />
              ))}
            </Chart>
          </ChartWrap>
          <TrendStats>
            <div>
              <dt>Earliest</dt>
              <dd>{first.risk_score}%</dd>
            </div>
            <div>
              <dt>Latest</dt>
              <dd>{latest.risk_score}%</dd>
            </div>
            <div>
              <dt>Change</dt>
              <dd>{change > 0 ? `+${change}` : change}</dd>
            </div>
          </TrendStats>
        </>
      ) : (
        <EmptyText>At least two scans are needed to show a trend.</EmptyText>
      )}
    </TrendPanel>
  );
}
