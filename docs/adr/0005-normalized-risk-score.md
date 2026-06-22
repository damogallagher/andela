# ADR 0005: Use A Normalized Weighted Risk Score

Status: Accepted

Date: 2026-06-23

## Context

The original risk score used `100 - flat_penalties`, capped at zero. That made the score easy to explain, but it created two problems:

- Four critical findings and ten critical findings could both report `0`.
- The same finding count meant the same score whether the scan covered one file or a larger infrastructure set.

The dashboard also color-codes the score, so the number needs to represent scan risk density rather than only a raw penalty total.

## Decision

Keep the score as a 0-100 health percentage, where `100` means no findings. For scans with findings, calculate a severity-weighted risk density:

- Severity weights: critical `10`, high `6`, medium `3`, low `1`.
- Scope units: `(files scanned * 2) + distinct affected resources`.
- Weighted risk density: `sum(severity weights) / scope units`.
- Score: `ceil((100 * 4 * scope units) / ((4 * scope units) + sum(severity weights)))`.

The formula is intentionally asymptotic instead of subtractive. Additional findings continue to lower the score, but the score does not collapse to zero after a small number of severe issues. Any scan with findings is capped at `99`, so only a clean scan can show `100`.

## Consequences

- Ten critical findings score lower than four critical findings.
- The same finding set scores higher when it is found in a broader scan scope.
- The score better aligns with the dashboard thresholds: green above `90`, amber from `70` to `90`, and red below `70`.
- The CLI guardrail remains severity-threshold based, so a normalized score does not hide critical findings from pipeline enforcement.
- This is still a challenge-focused heuristic, not a replacement for a full asset inventory, exploitability model, or business impact model.

## Alternatives Considered

- Keep flat penalties. Rejected because severe scans saturated at zero too quickly and ignored scan scope.
- Normalize only by file count. Rejected because multiple affected resources in one file should still change the density.
- Use CVSS-style scoring. Rejected because the scanner rules do not currently collect enough exploitability, exposure, and impact metadata to score honestly.
