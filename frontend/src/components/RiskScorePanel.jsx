import styled from "styled-components";

import { Eyebrow, Panel } from "./Panel.jsx";
import { theme } from "../styles.js";

const ScorePanel = styled(Panel)`
  grid-column: span 5;
  min-height: 180px;
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;

  @media (max-width: 920px) {
    grid-column: 1 / -1;
    align-items: stretch;
    flex-direction: column;
  }
`;

const Score = styled.h2`
  margin: 0;
  color: ${({ $scoreColor }) => $scoreColor || theme.colors.text};
  font-size: 4rem;
  line-height: 1;
`;

const Detail = styled.p`
  margin: 0;
  color: #607382;
`;

const Meter = styled.div`
  width: 112px;
  height: 112px;
  border-radius: 999px;
  background: conic-gradient(${({ $scoreColor }) => $scoreColor} calc(${({ $score }) => $score} * 1%), #dde6ea 0);
  display: grid;
  place-items: center;

  &::after {
    content: "";
    width: 72px;
    height: 72px;
    border-radius: 999px;
    background: #ffffff;
  }
`;

function scoreColor(score) {
  if (score > 90) {
    return theme.colors.scoreGreen;
  }
  if (score >= 70) {
    return theme.colors.scoreAmber;
  }
  return theme.colors.scoreRed;
}

export function RiskScorePanel({ scan }) {
  const score = scan?.risk_score ?? 0;
  const color = scan ? scoreColor(score) : theme.colors.text;

  return (
    <ScorePanel aria-labelledby="score-title">
      <div>
        <Eyebrow>Current Risk Score</Eyebrow>
        <Score id="score-title" $scoreColor={color}>{scan ? `${score}%` : "No scan"}</Score>
        <Detail>
          {scan ? `${scan.findings_count} findings across ${scan.files_scanned} files` : "Run the sample scan to populate the dashboard."}
        </Detail>
      </div>
      <Meter $score={score} $scoreColor={color} aria-hidden="true" />
    </ScorePanel>
  );
}
