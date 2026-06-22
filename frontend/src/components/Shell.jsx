import styled from "styled-components";

import { SecondaryLink } from "./Button.jsx";
import { theme } from "../styles.js";

const Header = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 28px clamp(20px, 5vw, 56px);
  border-bottom: 1px solid ${theme.colors.border};
  background: ${theme.colors.panel};

  @media (max-width: 760px) {
    align-items: stretch;
    flex-direction: column;
  }
`;

const Eyebrow = styled.p`
  margin: 0 0 6px;
  color: ${theme.colors.muted};
  font-size: 0.77rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
`;

const Title = styled.h1`
  margin: 0;
  color: ${theme.colors.text};
  font-size: clamp(1.7rem, 3vw, 2.55rem);
  line-height: 1.08;
`;

const Actions = styled.nav`
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
`;

export const Layout = styled.main`
  width: min(1600px, calc(100% - 24px));
  margin: 28px auto 48px;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 18px;
`;

export function Shell({ onRunSample, sampleBusy, onExportSarif, exportBusy, canExportSarif, children }) {
  return (
    <>
      <Header>
        <div>
          <Eyebrow>Local-only security scanner</Eyebrow>
          <Title>Enterprise Security Guardrail Auditor</Title>
        </div>
        <Actions aria-label="Primary actions">
          <RunSampleButton type="button" onClick={onRunSample} disabled={sampleBusy}>
            {sampleBusy ? "Scanning..." : "Run Sample Scan"}
          </RunSampleButton>
          <ExportSarifButton type="button" onClick={onExportSarif} disabled={!canExportSarif || exportBusy}>
            {exportBusy ? "Exporting..." : "Export SARIF"}
          </ExportSarifButton>
          <SecondaryLink href="/docs">API Docs</SecondaryLink>
        </Actions>
      </Header>
      {children}
    </>
  );
}

const RunSampleButton = styled.button`
  min-height: 40px;
  border: 1px solid ${theme.colors.teal};
  border-radius: 6px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: ${theme.colors.teal};
  font-weight: 800;
`;

const ExportSarifButton = styled.button`
  min-height: 40px;
  border: 1px solid ${theme.colors.teal};
  border-radius: 6px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #0f3f3b;
  background: ${theme.colors.tealSoft};
  font-weight: 800;
`;
