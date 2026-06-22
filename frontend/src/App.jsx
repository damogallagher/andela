import { useEffect, useMemo, useState } from "react";
import styled, { ThemeProvider } from "styled-components";

import { listScans, runSampleScan } from "./api.js";
import { FindingsTable } from "./components/FindingsTable.jsx";
import { Layout, Shell } from "./components/Shell.jsx";
import { RiskScorePanel } from "./components/RiskScorePanel.jsx";
import { ScanHistory } from "./components/ScanHistory.jsx";
import { SeverityCards } from "./components/SeverityCards.jsx";
import { UploadScan } from "./components/UploadScan.jsx";
import { GlobalStyle, theme } from "./styles.js";

function severityCounts(scan) {
  const counts = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const finding of scan?.findings || []) {
    counts[finding.severity] = (counts[finding.severity] || 0) + 1;
  }
  return counts;
}

function insertLatestScan(scans, scan) {
  return [scan, ...scans.filter((existing) => existing.id !== scan.id)].slice(0, 20);
}

export function App() {
  const [scans, setScans] = useState([]);
  const [selectedSeverity, setSelectedSeverity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sampleBusy, setSampleBusy] = useState(false);
  const [error, setError] = useState("");
  const latestScan = scans[0] || null;
  const counts = useMemo(() => severityCounts(latestScan), [latestScan]);

  useEffect(() => {
    let mounted = true;
    listScans()
      .then((items) => {
        if (mounted) {
          setScans(items);
        }
      })
      .catch((requestError) => {
        if (mounted) {
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  async function handleRunSample() {
    setSampleBusy(true);
    setError("");
    try {
      const scan = await runSampleScan();
      setScans((current) => insertLatestScan(current, scan));
      setSelectedSeverity(null);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSampleBusy(false);
    }
  }

  function handleScanCreated(scan) {
    setScans((current) => insertLatestScan(current, scan));
    setSelectedSeverity(null);
  }

  return (
    <ThemeProvider theme={theme}>
      <GlobalStyle />
      <Shell onRunSample={handleRunSample} sampleBusy={sampleBusy}>
        <Layout>
          {error ? <ErrorBanner role="alert">{error}</ErrorBanner> : null}
          {loading ? <LoadingBanner>Loading scans...</LoadingBanner> : null}
          <RiskScorePanel scan={latestScan} />
          <SeverityCards counts={counts} selectedSeverity={selectedSeverity} onSelect={setSelectedSeverity} />
          <UploadScan onScanCreated={handleScanCreated} />
          <FindingsTable scan={latestScan} selectedSeverity={selectedSeverity} onClearSeverity={() => setSelectedSeverity(null)} />
          <ScanHistory scans={scans} />
        </Layout>
      </Shell>
    </ThemeProvider>
  );
}

const ErrorBanner = styled.section`
  grid-column: 1 / -1;
  border: 1px solid #f2b7a0;
  border-radius: 8px;
  padding: 14px 16px;
  color: #7f1d1d;
  background: #fff1ed;
  font-weight: 800;
`;

const LoadingBanner = styled.section`
  grid-column: 1 / -1;
  border: 1px solid #dce4e8;
  border-radius: 8px;
  padding: 14px 16px;
  color: #526879;
  background: #ffffff;
  font-weight: 800;
`;
