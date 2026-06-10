import type {
  AnalysisStatus,
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
import { getStoredAuthToken, getStoredUserMode } from "./auth";
import { getGuestSessionHeaders } from "./guest-session";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const HEALTH_CHECK_TIMEOUT_MS = 5000;

interface ApiErrorPayload {
  detail?: string;
  error?: string;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

type ApiClaim = {
  id: string;
  text: string;
  confidence: number;
  status: ClaimStatus;
  claim_index: number;
  source_span: string | null;
};

type ApiEvidence = {
  id: string;
  claim_id: string;
  snippet: string;
  source_url: string | null;
  source_title: string | null;
  relevance_score: number;
  source_type: Evidence["sourceType"];
  polarity: Evidence["polarity"];
  retrieved_at: string;
};

type ApiTimelineEvent = {
  agent: string;
  started_at: string;
  completed_at: string;
  input_summary: string;
  output_summary: string;
};

type ApiAnalysisResponse = {
  id: string;
  status: AnalysisStatus;
  trust_score: number | null;
  hallucination_risk: AnalysisResponse["hallucinationRisk"];
  claims: ApiClaim[];
  evidence: ApiEvidence[];
  timeline?: ApiTimelineEvent[];
  critique: string | null;
  verdict: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
};

function toClaim(item: ApiClaim): Claim {
  return {
    id: item.id,
    text: item.text,
    confidence: item.confidence,
    status: item.status,
    claimIndex: item.claim_index,
    sourceSpan: item.source_span,
  };
}

function toEvidence(item: ApiEvidence): Evidence {
  return {
    id: item.id,
    claimId: item.claim_id,
    snippet: item.snippet,
    sourceUrl: item.source_url,
    sourceTitle: item.source_title,
    relevanceScore: item.relevance_score,
    sourceType: item.source_type,
    polarity: item.polarity,
    retrievedAt: item.retrieved_at,
  };
}

function toTimelineEvent(item: ApiTimelineEvent): TimelineEvent {
  return {
    agent: item.agent,
    startedAt: item.started_at,
    completedAt: item.completed_at,
    inputSummary: item.input_summary,
    outputSummary: item.output_summary,
  };
}

function toAnalysisResponse(item: ApiAnalysisResponse): AnalysisResponse {
  return {
    id: item.id,
    status: item.status,
    trustScore: item.trust_score,
    hallucinationRisk: item.hallucination_risk,
    claims: (item.claims ?? []).map(toClaim),
    evidence: (item.evidence ?? []).map(toEvidence),
    timeline: (item.timeline ?? []).map(toTimelineEvent),
    critique: item.critique,
    verdict: item.verdict,
    createdAt: item.created_at,
    completedAt: item.completed_at,
    error: item.error,
  };
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

function hasAuthorizationHeader(headers: HeadersInit): boolean {
  if (headers instanceof Headers) {
    return headers.has("Authorization");
  }

  if (Array.isArray(headers)) {
    return headers.some(([name]) => name.toLowerCase() === "authorization");
  }

  return Object.keys(headers).some((name) => name.toLowerCase() === "authorization");
}

function isLocalAuthToken(token: string | null): boolean {
  return typeof token === "string" && token.startsWith("local:");
}

function withGuestSessionHeaders(headers: HeadersInit = {}): HeadersInit {
  const authToken = getStoredAuthToken();
  if (hasAuthorizationHeader(headers)) {
    return headers;
  }

  if (getStoredUserMode() === "AUTHENTICATED" && authToken && !isLocalAuthToken(authToken)) {
    return headers;
  }

  const guestHeaders = getGuestSessionHeaders();
  if (!guestHeaders) {
    return headers;
  }

  if (headers instanceof Headers) {
    const merged = new Headers(headers);
    for (const [name, value] of Object.entries(guestHeaders)) {
      merged.set(name, value);
    }
    return merged;
  }

  if (Array.isArray(headers)) {
    return [...headers, ...Object.entries(guestHeaders)];
  }

  return {
    ...headers,
    ...guestHeaders,
  };
}

function withAuthorizationHeader(headers: HeadersInit = {}): HeadersInit {
  if (hasAuthorizationHeader(headers)) {
    return headers;
  }

  const authToken = getStoredAuthToken();
  if (!authToken || isLocalAuthToken(authToken)) {
    return headers;
  }

  if (headers instanceof Headers) {
    const merged = new Headers(headers);
    merged.set("Authorization", `Bearer ${authToken}`);
    return merged;
  }

  if (Array.isArray(headers)) {
    return [...headers, ["Authorization", `Bearer ${authToken}`]];
  }

  return {
    ...headers,
    Authorization: `Bearer ${authToken}`,
  };
}

function withRequestHeaders(headers: HeadersInit = {}): HeadersInit {
  return withAuthorizationHeader(withGuestSessionHeaders(headers));
}

async function apiGet<T>(path: string, headers: HeadersInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...withRequestHeaders(headers),
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
      ...withRequestHeaders(headers),
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return (await response.json()) as T;
}

export async function checkBackendHealth(): Promise<void> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT_MS);

  try {
    const response = await fetch(`${BASE_URL}/api/v1/health`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw await parseApiError(response);
    }
  } finally {
    window.clearTimeout(timeoutId);
  }
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

export async function submitAnalysis(request: AnalysisRequest): Promise<{ id: string }> {
  const payload = await apiPost<{ id: string; status: string }>("/api/v1/analyze", {
    prompt: request.prompt,
    response: request.response,
    model_name: request.modelName,
    include_comparison: request.includeComparison,
  });

  return { id: payload.id };
}

export async function getAnalysis(analysisId: string): Promise<AnalysisResponse> {
  const payload = await apiGet<ApiAnalysisResponse>(`/api/v1/analyze/${analysisId}`);
  return toAnalysisResponse(payload);
}

export async function getClaims(analysisId: string, status?: ClaimStatus): Promise<Claim[]> {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
  const payload = await apiGet<ApiClaim[]>(`/api/v1/analyze/${analysisId}/claims${suffix}`);
  return payload.map(toClaim);
}

export async function getEvidence(analysisId: string, claimId?: string): Promise<Evidence[]> {
  const suffix = claimId ? `?claim_id=${encodeURIComponent(claimId)}` : "";
  const payload = await apiGet<ApiEvidence[]>(`/api/v1/analyze/${analysisId}/evidence${suffix}`);
  return payload.map(toEvidence);
}

export async function getTimeline(analysisId: string): Promise<TimelineEvent[]> {
  const payload = await apiGet<ApiTimelineEvent[]>(`/api/v1/analyze/${analysisId}/timeline`);
  return payload.map(toTimelineEvent);
}

export async function compareModels(request: ComparisonRequest): Promise<ComparisonResponse> {
  const payload = await apiPost<{ analyses: ApiAnalysisResponse[] }>("/api/v1/compare", request);
  return {
    analyses: payload.analyses.map(toAnalysisResponse),
  };
}
