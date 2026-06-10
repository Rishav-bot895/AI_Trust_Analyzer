export type ClaimStatus =
  | "SUPPORTED"
  | "PARTIALLY_SUPPORTED"
  | "CONTRADICTED"
  | "UNSUPPORTED"
  | "UNVERIFIABLE";

export type EvidenceSource = "WEB_SEARCH" | "PGVECTOR";

export type EvidencePolarity = "FOR" | "AGAINST";

export type AnalysisStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export type HallucinationRisk = "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN";

export type UserMode = "AUTHENTICATED" | "GUEST";

export interface Claim {
  id: string;
  text: string;
  confidence: number;
  status: ClaimStatus;
  claimIndex: number;
  sourceSpan: string | null;
}

export interface Evidence {
  id: string;
  claimId: string;
  snippet: string;
  sourceUrl: string | null;
  sourceTitle: string | null;
  relevanceScore: number;
  sourceType: EvidenceSource;
  polarity: EvidencePolarity | null;
  retrievedAt: string;
}

export interface TimelineEvent {
  agent: string;
  startedAt: string;
  completedAt: string;
  inputSummary: string;
  outputSummary: string;
}

export interface AnalysisResponse {
  id: string;
  status: AnalysisStatus;
  trustScore: number | null;
  hallucinationRisk: HallucinationRisk | null;
  claims: Claim[];
  evidence: Evidence[];
  timeline: TimelineEvent[];
  critique: string | null;
  verdict: string | null;
  createdAt: string;
  completedAt: string | null;
  error: string | null;
}

export interface AnalysisListItem {
  id: string;
  status: AnalysisStatus;
  trustScore: number | null;
  hallucinationRisk: HallucinationRisk | null;
  createdAt: string;
  completedAt: string | null;
  error: string | null;
}

export interface AnalysisRequest {
  prompt: string;
  response: string;
  modelName?: string;
  userMode: UserMode;
  guestSessionId?: string;
}

export interface ComparisonRequest {
  prompt: string;
  response: string;
  models?: string[];
}

export interface ComparisonResponse {
  analyses: AnalysisResponse[];
}
