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
  procedure_cpt_codes: string[] | null;
  conservative_treatments_failed: string[] | null;
  implant_type_requested: string | null;
  robotic_assistance_required: boolean | null;
  clinical_justification: string | null;
  confidence_score: number | null;
  outcome: string | null;
}

export type PriorAuthOutcome = "pending" | "approved" | "denied" | "appealed";

export async function updateOutcome(extractionId: string, outcome: PriorAuthOutcome): Promise<void> {
  const res = await fetch(`${API_BASE}/extraction/${extractionId}/outcome`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ outcome }),
  });
  if (!res.ok) throw new Error(await res.text());
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  source_type: string;
  created_at: string;
  extraction_result: ExtractionResult | null;
  error_message: string | null;
}

export interface Citation {
  marker: string;
  claim: string;
  source_type: string;
  source_text: string | null;
  section_title: string | null;
}

export interface NarrativeResponse {
  narrative_id: string;
  narrative_text: string;
  model_used: string;
  prompt_version: string;
  payer: string | null;
  procedure: string | null;
  citations: Citation[] | null;
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

export async function uploadClinicalNoteText(text: string, caseId?: string): Promise<IngestionResponse> {
  const params = caseId ? `?case_id=${caseId}` : "";
  const res = await fetch(`${API_BASE}/ingest/clinical-note/text${params}`, {
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

export async function generateNarrative(
  extractionId: string,
  payer?: string | null,
  procedure?: string | null,
): Promise<NarrativeResponse> {
  const body: Record<string, string> = {};
  if (payer) body.payer = payer;
  if (procedure) body.procedure = procedure;

  const res = await fetch(`${API_BASE}/extraction/${extractionId}/narrative`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchPayers(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/policies/payers`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchProcedures(payer?: string): Promise<string[]> {
  const url = payer
    ? `${API_BASE}/policies/procedures?payer=${encodeURIComponent(payer)}`
    : `${API_BASE}/policies/procedures`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface PayerReadinessResponse {
  payer: string;
  procedure: string;
  readiness_score: number;
  gaps: string[];
  submission_portal: string;
  criteria: Record<string, unknown>;
}

export async function checkPayerReadiness(
  payer: string,
  procedure: string,
  treatmentsCount: number,
  hasImaging: boolean,
  symptomMonths: number,
): Promise<PayerReadinessResponse> {
  const params = new URLSearchParams({
    payer,
    procedure,
    treatments_count: String(treatmentsCount),
    has_imaging: String(hasImaging),
    symptom_months: String(symptomMonths),
  });
  const res = await fetch(`${API_BASE}/policies/check?${params}`);
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

export async function fetchCitations(narrativeId: string): Promise<Citation[]> {
  const res = await fetch(`${API_BASE}/citations/${narrativeId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface PolicyChunk {
  id: string;
  payer: string;
  procedure: string | null;
  section_title: string | null;
  content: string;
  chunk_index: number;
}

export async function fetchPolicyChunks(payer?: string, procedure?: string): Promise<PolicyChunk[]> {
  const params = new URLSearchParams();
  if (payer) params.set("payer", payer);
  if (procedure) params.set("procedure", procedure);
  const res = await fetch(`${API_BASE}/policy-docs/chunks?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface GraphInsight {
  type: string;
  payer?: string;
  requirement: string;
  criterion_type?: string;
}

export async function fetchGraphInsights(procedure: string, diagnosisCode?: string): Promise<GraphInsight[]> {
  const params = new URLSearchParams({ procedure });
  if (diagnosisCode) params.set("diagnosis_code", diagnosisCode);
  const res = await fetch(`${API_BASE}/graph/insights?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// --- Cases ---

export interface CaseResponse {
  id: string;
  short_id: string;
  label: string | null;
  status: string;
  denial_reason: string | null;
  created_at: string;
  document_count: number;
}

export async function createCase(label?: string): Promise<CaseResponse> {
  const res = await fetch(`${API_BASE}/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(label ? { label } : {}),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listCases(status?: string): Promise<CaseResponse[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const res = await fetch(`${API_BASE}/cases?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getCase(shortId: string): Promise<CaseResponse> {
  const res = await fetch(`${API_BASE}/cases/${shortId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// --- Narrative Editing ---

export interface NarrativeVersion {
  id: string;
  version_number: number;
  narrative_text: string;
  source: string;
  created_at: string;
}

export async function editNarrative(narrativeId: string, text: string): Promise<{ version: number }> {
  const res = await fetch(`${API_BASE}/narrative/${narrativeId}/edit`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ narrative_text: text }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getNarrativeVersions(narrativeId: string): Promise<NarrativeVersion[]> {
  const res = await fetch(`${API_BASE}/narrative/${narrativeId}/versions`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function revertNarrative(narrativeId: string, versionNumber: number): Promise<void> {
  const res = await fetch(`${API_BASE}/narrative/${narrativeId}/revert/${versionNumber}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
}

// --- Appeal ---

export async function generateAppeal(
  extractionId: string,
  denialReason: string,
  additionalContext?: string,
): Promise<NarrativeResponse> {
  const res = await fetch(`${API_BASE}/extraction/${extractionId}/appeal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      denial_reason: denialReason,
      additional_context: additionalContext,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
