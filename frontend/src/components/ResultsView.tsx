"use client";

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { AnalysisListItem, AnalysisResponse, ClaimStatus, ComparisonResponse } from "../types/api";
import { useHistory } from "../hooks/useHistory";
import { TrustScoreCard } from "./TrustScoreCard";
import { ClaimsTable } from "./ClaimsTable";
import { EvidencePanel } from "./EvidencePanel";
import { AgentTimeline } from "./AgentTimeline";
import { ModelComparisonTable } from "./ModelComparisonTable";
import { TabNavigation, type TabId } from "./TabNavigation";
import { ResultsSkeleton, ShimmerStyles } from "./SkeletonLoader";
import { modelLabel } from "../lib/models";

interface ResultsViewProps {
  analysis?: AnalysisResponse;
  result?: AnalysisResponse;
  comparison?: ComparisonResponse;
  comparisonModels?: string[];
  showHistoryTab?: boolean;
  authToken?: string | null;
  history?: AnalysisListItem[];
}

const CLAIM_STATUS_LABELS: Record<ClaimStatus, string> = {
  SUPPORTED: "Supported",
  PARTIALLY_SUPPORTED: "Partial",
  CONTRADICTED: "Contradicted",
  UNSUPPORTED: "Unsupported",
  UNVERIFIABLE: "Unverifiable",
};

function formatDate(value: string | null): string {
  if (!value) return "In progress";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function CritiqueSection({ critique }: { critique: string | null }) {
  if (!critique) return null;

  return (
    <section className="card p-6" aria-labelledby="critique-heading">
      <p id="critique-heading" className="label mb-3">Critique</p>
      <div className="prose-trust text-sm leading-relaxed text-text-secondary">
        <ReactMarkdown
          components={{
            h1: ({ children }) => <h1 className="mt-4 text-lg font-semibold text-text-primary first:mt-0">{children}</h1>,
            h2: ({ children }) => <h2 className="mt-4 text-base font-semibold text-text-primary first:mt-0">{children}</h2>,
            h3: ({ children }) => <h3 className="mt-3 text-sm font-semibold text-text-primary first:mt-0">{children}</h3>,
            p: ({ children }) => <p className="mt-2 first:mt-0">{children}</p>,
            ul: ({ children }) => <ul className="mt-2 list-disc space-y-1 pl-5">{children}</ul>,
            ol: ({ children }) => <ol className="mt-2 list-decimal space-y-1 pl-5">{children}</ol>,
            li: ({ children }) => <li>{children}</li>,
            strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
          }}
        >
          {critique}
        </ReactMarkdown>
      </div>
    </section>
  );
}

function OriginalTextBlock({
  title,
  value,
}: {
  title: string;
  value: string | null;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const text = value?.trim() || "Not available.";
  const isLong = text.length > 700;
  const visibleText = !isExpanded && isLong ? `${text.slice(0, 700).trimEnd()}...` : text;

  async function copyText() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="rounded-md border border-border bg-surface-high p-4" aria-label={title}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="label">{title}</p>
        <div className="flex items-center gap-2">
          {isLong ? (
            <button
              type="button"
              onClick={() => setIsExpanded((current) => !current)}
              className="rounded border border-border px-3 py-1 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent"
            >
              {isExpanded ? "Collapse" : "Expand"}
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => void copyText()}
            className="rounded border border-border px-3 py-1 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
      <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap break-words rounded border border-border-subtle bg-surface p-3 text-sm leading-relaxed text-text-secondary">
        {visibleText}
      </pre>
    </section>
  );
}

function OriginalInputSection({ analysis }: { analysis: AnalysisResponse }) {
  return (
    <section className="space-y-3" aria-labelledby="original-input-heading">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="label">Analysis Results</p>
          <h2 id="original-input-heading" className="text-xl text-text-primary" style={{ fontFamily: "var(--font-serif)" }}>
            Original Input
          </h2>
        </div>
        <span className="rounded-full border border-border bg-surface-high px-3 py-1 text-xs text-text-secondary">
          Response model: {modelLabel(analysis.modelName)}
        </span>
      </div>
      <OriginalTextBlock title="Original Prompt" value={analysis.prompt} />
      <OriginalTextBlock title="AI Response" value={analysis.response} />
    </section>
  );
}

function HistoryPanel({
  analysis,
  history,
  isLoading,
  error,
  onReload,
}: {
  analysis: AnalysisResponse;
  history: AnalysisListItem[];
  isLoading: boolean;
  error: string | null;
  onReload: () => void;
}) {
  const statusCounts = useMemo(() => {
    return analysis.claims.reduce<Partial<Record<ClaimStatus, number>>>((counts, claim) => {
      counts[claim.status] = (counts[claim.status] ?? 0) + 1;
      return counts;
    }, {});
  }, [analysis.claims]);

  return (
    <section id="panel-history" role="tabpanel" aria-labelledby="tab-history" className="space-y-4">
      <div className="rounded-md border border-border bg-surface-high p-4">
        <p className="label">Claim Summary</p>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5">
          {(Object.keys(CLAIM_STATUS_LABELS) as ClaimStatus[]).map((status) => (
            <div key={status} className="rounded border border-border bg-surface px-3 py-2">
              <p className="text-[11px] uppercase tracking-wide text-text-muted">{CLAIM_STATUS_LABELS[status]}</p>
              <p className="mt-1 text-lg font-semibold text-text-primary">{statusCounts[status] ?? 0}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-md border border-border bg-surface-high p-4">
        <div className="flex items-center justify-between gap-3">
          <p className="label">Previous Analyses</p>
          <button
            type="button"
            onClick={onReload}
            className="rounded border border-border px-3 py-1 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent"
          >
            Refresh
          </button>
        </div>

        {isLoading ? (
          <p className="mt-2 text-sm text-text-muted">Loading history...</p>
        ) : null}

        {error ? (
          <p className="mt-2 text-sm text-refuted">{error}</p>
        ) : null}

        {!isLoading && !error && history.length === 0 ? (
          <p className="mt-2 text-sm text-text-muted">No previous analyses available for this account.</p>
        ) : null}

        {!isLoading && !error && history.length > 0 ? (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="pb-2 pr-4"><span className="label">Created</span></th>
                  <th className="pb-2 pr-4"><span className="label">Status</span></th>
                  <th className="pb-2 pr-4"><span className="label">Score</span></th>
                  <th className="pb-2 pr-4"><span className="label">Risk</span></th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id} className="border-b border-border-subtle last:border-b-0">
                    <td className="py-2 pr-4 text-text-secondary">{formatDate(item.createdAt)}</td>
                    <td className="py-2 pr-4 text-text-secondary">{item.status}</td>
                    <td className="py-2 pr-4 text-text-primary">{item.trustScore ?? "--"}</td>
                    <td className="py-2 pr-4 text-text-secondary">{item.hallucinationRisk ?? "--"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function firstEnabledTab(disabledTabs: TabId[], showHistoryTab: boolean): TabId {
  const tabOrder: TabId[] = showHistoryTab
    ? ["claims", "evidence", "timeline", "compare", "history"]
    : ["claims", "evidence", "timeline", "compare"];

  return tabOrder.find((tab) => !disabledTabs.includes(tab)) ?? "claims";
}

export function ResultsView({
  analysis: analysisProp,
  result,
  comparison,
  comparisonModels = [],
  showHistoryTab = false,
  authToken = null,
  history = [],
}: ResultsViewProps) {
  const analysis = analysisProp ?? result;
  const [activeTab, setActiveTab] = useState<TabId>("claims");
  const {
    history: fetchedHistory,
    isLoading: isHistoryLoading,
    error: historyError,
    reload: reloadHistory,
  } = useHistory(showHistoryTab, authToken);
  const displayedHistory = history.length > 0 ? history : fetchedHistory;

  const counts = useMemo<Partial<Record<TabId, number>>>(() => ({
    claims: analysis?.claims.length ?? 0,
    evidence: analysis?.evidence.length ?? 0,
    timeline: analysis?.timeline?.length ?? 0,
    compare: comparison?.analyses.length ?? 0,
    history: displayedHistory.length,
  }), [analysis, comparison, displayedHistory.length]);

  const disabledTabs = useMemo<TabId[]>(() => [
    ...((analysis?.claims.length ?? 0)   === 0 ? ["claims"]     as TabId[] : []),
    ...((analysis?.evidence.length ?? 0) === 0 ? ["evidence"]   as TabId[] : []),
    ...(!comparison              ? ["compare"] as TabId[] : []),
  ], [analysis, comparison]);
  const currentTab = disabledTabs.includes(activeTab)
    ? firstEnabledTab(disabledTabs, showHistoryTab)
    : activeTab;

  if (!analysis || analysis.status !== "COMPLETED") {
    return (
      <div aria-label="results-loading-skeleton">
        <ResultsSkeleton />
        <ShimmerStyles />
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">

      <OriginalInputSection analysis={analysis} />

      <TrustScoreCard
        trustScore={analysis.trustScore}
        hallucinationRisk={analysis.hallucinationRisk}
        verdict={analysis.verdict}
        isLoading={analysis.trustScore === null}
      />

      <CritiqueSection critique={analysis.critique} />

      <div className="overflow-hidden rounded-lg border border-border bg-surface-raised">
        <TabNavigation
          activeTab={currentTab}
          onChange={setActiveTab}
          counts={counts}
          disabledTabs={disabledTabs}
          showHistoryTab={showHistoryTab}
        />

        <div className="p-4">
          {currentTab === "claims" && (
            <div id="panel-claims" role="tabpanel" aria-labelledby="tab-claims">
              <ClaimsTable claims={analysis.claims} evidence={analysis.evidence} />
            </div>
          )}

          {currentTab === "evidence" && (
            <div id="panel-evidence" role="tabpanel" aria-labelledby="tab-evidence">
              <EvidencePanel
                evidence={analysis.evidence}
                claims={analysis.claims.map((c) => ({
                  id: c.id,
                  text: c.text,
                  claimIndex: c.claimIndex,
                }))}
              />
            </div>
          )}

          {currentTab === "timeline" && (
            <div id="panel-timeline" role="tabpanel" aria-labelledby="tab-timeline">
              <AgentTimeline timeline={analysis.timeline ?? []} />
            </div>
          )}

          {currentTab === "compare" && comparison && (
            <div id="panel-compare" role="tabpanel" aria-labelledby="tab-compare">
              <ModelComparisonTable
                analyses={comparison.analyses}
                models={comparisonModels}
              />
            </div>
          )}

          {currentTab === "history" && showHistoryTab && (
            <HistoryPanel
              analysis={analysis}
              history={displayedHistory}
              isLoading={isHistoryLoading}
              error={historyError}
              onReload={reloadHistory}
            />
          )}
        </div>
      </div>
    </div>
  );
}
