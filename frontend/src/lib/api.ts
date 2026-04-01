// All API calls go through the Next.js proxy at /api/proxy/...
// The proxy adds the API key server-side — never exposed to the browser.
const API_BASE = "/api/proxy/api/v1";

export interface IngestionResponse {
  job_id: string;
  status: string;
  message?: string;
  metadata?: Record<string, unknown>;
  file_key?: string;
}

export interface ExtractionResult {
  id: string;
  diagnosis_code: string | null;
  conservative_treatments_failed: string[] | null;
  implant_type_requested: string | null;
  robotic_assistance_required: boolean | null;
  clinical_justification: string | null;
  confidence_score: number | null;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  source_type: string;
  created_at: string;
  extraction_result: ExtractionResult | null;
  error_message: string | null;
}

export interface NarrativeResponse {
  narrative_id: string;
  narrative_text: string;
  model_used: string;
  prompt_version: string;
}

export async function uploadDicom(file: File): Promise<IngestionResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/ingest/dicom`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadClinicalNote(file: File): Promise<IngestionResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/ingest/clinical-note`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadRoboticReport(file: File): Promise<IngestionResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/ingest/robotic-report`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadClinicalNoteText(text: string): Promise<IngestionResponse> {
  const res = await fetch(`${API_BASE}/ingest/clinical-note/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/ingest/jobs/${jobId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generateNarrative(extractionId: string): Promise<NarrativeResponse> {
  const res = await fetch(`${API_BASE}/extraction/${extractionId}/narrative`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function retryJob(jobId: string): Promise<IngestionResponse> {
  const res = await fetch(`${API_BASE}/ingest/jobs/${jobId}/retry`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exportNarrativePdf(extractionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/extraction/${extractionId}/export/pdf`);
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `prior-auth-${extractionId.slice(0, 8)}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}

export function getSSEUrl(jobId: string): string {
  return `${API_BASE}/ingest/jobs/${jobId}/status`;
}
