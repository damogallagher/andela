import { useState } from "react";
import styled from "styled-components";

import { PrimaryButton } from "./Button.jsx";
import { Eyebrow, Panel, SectionHeader, SectionTitle } from "./Panel.jsx";
import { uploadScan } from "../api.js";
import { theme } from "../styles.js";

const UploadPanel = styled(Panel)`
  grid-column: 1 / -1;
  padding: 24px;
`;

const Form = styled.form`
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(260px, 1.4fr) auto;
  align-items: end;
  gap: 14px;

  @media (max-width: 920px) {
    grid-template-columns: 1fr;
  }
`;

const Field = styled.label`
  display: grid;
  gap: 7px;
  color: ${theme.colors.muted};
  font-size: 0.82rem;
  font-weight: 800;
`;

const Input = styled.input`
  min-height: 40px;
  width: 100%;
  border: 1px solid ${theme.colors.borderStrong};
  border-radius: 6px;
  padding: 8px 10px;
  color: ${theme.colors.text};
  background: #ffffff;
  font-weight: 500;
`;

const Status = styled.p`
  grid-column: 1 / -1;
  min-height: 20px;
  margin: 0;
  color: #8a3b12;
  font-size: 0.9rem;
  font-weight: 800;
`;

export function UploadScan({ onScanCreated }) {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    setBusy(true);
    setStatus("");
    try {
      const scan = await uploadScan(formData);
      onScanCreated(scan);
      setStatus("Scan complete.");
      form.reset();
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <UploadPanel aria-labelledby="upload-title">
      <SectionHeader>
        <div>
          <Eyebrow>Upload scan</Eyebrow>
          <SectionTitle id="upload-title">Scan Files</SectionTitle>
        </div>
      </SectionHeader>
      <Form onSubmit={handleSubmit}>
        <Field>
          <span>Scan label</span>
          <Input name="label" type="text" defaultValue="Uploaded file scan" maxLength={120} />
        </Field>
        <Field>
          <span>Infrastructure files</span>
          <Input name="files" type="file" accept=".tf,.json,.template,.yaml,.yml" multiple required />
        </Field>
        <PrimaryButton type="submit" disabled={busy}>{busy ? "Scanning..." : "Scan Upload"}</PrimaryButton>
        <Status role="status">{status}</Status>
      </Form>
    </UploadPanel>
  );
}
