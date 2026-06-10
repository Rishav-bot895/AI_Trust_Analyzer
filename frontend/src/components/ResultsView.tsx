"use client";

import { useState } from "react";
import type { AnalysisResponse, ComparisonResponse } from "../types/api";
import { TrustScoreCard } from "./TrustScoreCard";
import { ClaimsTable } from "./ClaimsTable";
import { EvidencePanel } from "./EvidencePanel";
import { AgentTimeline } from "./AgentTimeline";
import { ModelComparisonTable } from "./ModelComparisonTable";
import { TabNavigation, type TabId } from "./TabNavigation";

interface ResultsViewProps {
  result: AnalysisResponse;
  comparison?: ComparisonResponse;
  comparisonModels?: string[];
}

export function ResultsView({ result, comparison, comparisonModels = [] }: ResultsViewProps) {
  const [activeTab, setActiveTab] = useState<TabId>("results");

  const counts: Partial<Record<TabId, number>> = {
    claims:     result.claims.length,
    evidence:   result.evidence.length,
    timeline:   result.timeline?.length ?? 0,
    comparison: comparison?.analyses.length ?? 0,
  };

  const disabledTabs: TabId[] = [
    ...(result.claims.length   === 0 ? ["claims"]     as TabId[] : []),
    ...(result.evidence.length === 0 ? ["evidence"]   as TabId[] : []),
    ...(!result.timeline || result.timeline.length === 0 ? ["timeline"] as TabId[] : []),
    ...(!comparison              ? ["comparison"] as TabId[] : []),
  ];

  return (
    <div className="w-full space-y-4">

      {/* Always-visible score card */}
      <TrustScoreCard
        trustScore={result.trustScore}
        hallucinationRisk={result.hallucinationRisk}
        verdict={result.verdict}
        critique={result.critique}
      />

      {/* Tab bar + panels */}
      <div className="card overflow-hidden">
        <TabNavigation
          activeTab={activeTab}
          onChange={setActiveTab}
          counts={counts}
          disabledTabs={disabledTabs}
        />

        <div className="p-4">
          {activeTab === "results" && (
            <div className="space-y-2">
              {/* Quick stat row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "Claims",      value: result.claims.length },
                  { label: "Supported",   value: result.claims.filter((c) => c.status === "SUPPORTED").length,     color: "var(--color-verified)" },
                  { label: "Contradicted",value: result.claims.filter((c) => c.status === "CONTRADICTED").length,  color: "var(--color-refuted)"  },
                  { label: "Evidence",    value: result.evidence.length },
                ].map((stat) => (
                  <div key={stat.label} className="card-high p-3 space-y-1">
                    <p className="label">{stat.label}</p>
                    <p
                      className="text-2xl font-medium"
                      style={{ color: stat.color ?? "var(--color-text-primary)" }}
                    >
                      {stat.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Error state */}
              {result.error && (
                <div
                  className="rounded-md p-4 text-sm"
                  style={{
                    background: "rgba(239,68,68,0.08)",
                    border: "1px solid rgba(239,68,68,0.3)",
                    color: "var(--color-refuted)",
                  }}
                >
                  <p className="font-medium mb-1">Analysis Error</p>
                  <p className="text-xs opacity-80">{result.error}</p>
                </div>
              )}
            </div>
          )}

          {activeTab === "claims" && (
            <ClaimsTable claims={result.claims} />
          )}

          {activeTab === "evidence" && (
            <EvidencePanel
              evidence={result.evidence}
              claims={result.claims.map((c) => ({
                id: c.id,
                text: c.text,
                claimIndex: c.claimIndex,
              }))}
            />
          )}

          {activeTab === "timeline" && (
            <AgentTimeline timeline={result.timeline ?? []} />
          )}

          {activeTab === "comparison" && comparison && (
            <ModelComparisonTable
              analyses={comparison.analyses}
              models={comparisonModels}
            />
          )}
        </div>
      </div>
    </div>
  );
}