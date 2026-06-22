async function request(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed with status ${response.status}`);
  }
  return response.json();
}

async function download(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed with status ${response.status}`);
  }
  return response.blob();
}

export function listScans() {
  return request("/api/scans");
}

export function runSampleScan() {
  return request("/api/scans/sample", { method: "POST" });
}

export function uploadScan(formData) {
  return request("/api/scans/upload", {
    method: "POST",
    body: formData,
  });
}

export function exportScanSarif(scanId) {
  return download(`/api/scans/${scanId}/sarif`, {
    headers: {
      Accept: "application/sarif+json",
    },
  });
}
