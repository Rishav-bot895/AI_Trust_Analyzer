import type {
  AnalysisListItem,
  AnalysisRequest,
  AnalysisResponse,
  Claim,
  ClaimStatus,
  ComparisonRequest,
  ComparisonResponse,
  Evidence,
  TimelineEvent,
} from "../types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ApiErrorPayload {
  detail?: string;
  error?: string;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.name = "ApiError";
  }
}

function toAnalysisListItem(item: {
  id: string;
  status: AnalysisListItem["status"];
  trust_score: number | null;
  hallucination_risk: AnalysisListItem["hallucinationRisk"];
  created_at: string;
  completed_at: string | null;
  error: string | null;
}): AnalysisListItem {
  return {
    id: item.id,
    status: item.status,
    trustScore: item.trust_score,
    hallucinationRisk: item.hallucination_risk,
    createdAt: item.created_at,
    completedAt: item.completed_at,
    error: item.error,
  };
}

async function parseApiError(response: Response): Promise<ApiError> {
  let detail = `Request failed with status ${response.status}`;
  try {
    const body = (await response.json()) as ApiErrorPayload;
    detail = body.detail ?? body.error ?? detail;
  } catch {
    // Keep fallback message when backend does not return JSON.
  }
  return new ApiError(response.status, detail);
}

async function apiGet<T>(path: string, headers: HeadersInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return (await response.json()) as T;
}

async function apiPost<T>(path: string, body: unknown, headers: HeadersInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return (await response.json()) as T;
}

export async function getAuthenticatedHistory(
  accessToken: string,
  params?: { limit?: number; offset?: number },
): Promise<AnalysisListItem[]> {
  const query = new URLSearchParams();
  if (typeof params?.limit === "number") {
    query.set("limit", String(params.limit));
  }
  if (typeof params?.offset === "number") {
    query.set("offset", String(params.offset));
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  const payload = await apiGet<
    Array<{
    id: string;
    status: AnalysisListItem["status"];
    trust_score: number | null;
    hallucination_risk: AnalysisListItem["hallucinationRisk"];
    created_at: string;
    completed_at: string | null;
    error: string | null;
    }>
  >(`/api/v1/analyze/history${suffix}`, {
    Authorization: `Bearer ${accessToken}`,
  });

  return payload.map(toAnalysisListItem);
}

export async function submitAnalysis(request: AnalysisRequest): Promise<{ id: string; status: string }> {
  return apiPost<{ id: string; status: string }>("/api/v1/analyze", request);
}

export async function getAnalysis(analysisId: string): Promise<AnalysisResponse> {
  return apiGet<AnalysisResponse>(`/api/v1/analyze/${analysisId}`);
}

export async function getClaims(analysisId: string, status?: ClaimStatus): Promise<Claim[]> {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiGet<Claim[]>(`/api/v1/analyze/${analysisId}/claims${suffix}`);
}

export async function getEvidence(analysisId: string, claimId?: string): Promise<Evidence[]> {
  const suffix = claimId ? `?claim_id=${encodeURIComponent(claimId)}` : "";
  return apiGet<Evidence[]>(`/api/v1/analyze/${analysisId}/evidence${suffix}`);
}

export async function getTimeline(analysisId: string): Promise<TimelineEvent[]> {
  return apiGet<TimelineEvent[]>(`/api/v1/analyze/${analysisId}/timeline`);
}

export async function compareModels(request: ComparisonRequest): Promise<ComparisonResponse> {
  return apiPost<ComparisonResponse>("/api/v1/compare", request);
}
