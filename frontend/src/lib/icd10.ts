/**
 * Common orthopaedic ICD-10 codes with human-readable descriptions.
 * Covers the most frequent codes seen in ASC prior auth workflows.
 */
export const ICD10_DESCRIPTIONS: Record<string, string> = {
  // Knee
  "M17.0": "Bilateral primary osteoarthritis of knee",
  "M17.10": "Primary osteoarthritis, unspecified knee",
  "M17.11": "Primary osteoarthritis, right knee",
  "M17.12": "Primary osteoarthritis, left knee",
  "M17.2": "Post-traumatic osteoarthritis, bilateral knees",
  "M17.30": "Post-traumatic osteoarthritis, unspecified knee",
  "M17.31": "Post-traumatic osteoarthritis, right knee",
  "M17.32": "Post-traumatic osteoarthritis, left knee",
  "M23.51": "Chronic instability of knee, right",
  "M23.52": "Chronic instability of knee, left",

  // Hip
  "M16.0": "Bilateral primary osteoarthritis of hip",
  "M16.10": "Primary osteoarthritis, unspecified hip",
  "M16.11": "Primary osteoarthritis, right hip",
  "M16.12": "Primary osteoarthritis, left hip",
  "M16.2": "Bilateral osteoarthritis of hip from dysplasia",
  "M16.30": "Post-traumatic osteoarthritis, unspecified hip",
  "M16.31": "Post-traumatic osteoarthritis, right hip",
  "M16.32": "Post-traumatic osteoarthritis, left hip",
  "M87.051": "Avascular necrosis, right femur",
  "M87.052": "Avascular necrosis, left femur",

  // Shoulder
  "M75.10": "Rotator cuff tear, unspecified shoulder",
  "M75.11": "Rotator cuff tear, right shoulder",
  "M75.12": "Rotator cuff tear, left shoulder",
  "M19.011": "Primary osteoarthritis, right shoulder",
  "M19.012": "Primary osteoarthritis, left shoulder",

  // Spine
  "M47.816": "Spondylosis with myelopathy, lumbar",
  "M51.16": "Intervertebral disc disorders with radiculopathy, lumbar",
  "M54.5": "Low back pain",
};

export function getICD10Description(code: string): string | null {
  return ICD10_DESCRIPTIONS[code] || null;
}
