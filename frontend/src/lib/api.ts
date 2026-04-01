const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  const res = await fetch(`${API_URL}/api/v1/ingest/dicom`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadClinicalNote(file: File): Promise<IngestionResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/v1/ingest/clinical-note`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadRoboticReport(file: File): Promise<IngestionResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/v1/ingest/robotic-report`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_URL}/api/v1/ingest/jobs/${jobId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generateNarrative(extractionId: string): Promise<NarrativeResponse> {
  const res = await fetch(`${API_URL}/api/v1/extraction/${extractionId}/narrative`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function getSSEUrl(jobId: string): string {
  return `${API_URL}/api/v1/ingest/jobs/${jobId}/status`;
}
