"use client";

import { useEffect, useMemo, useRef } from "react";

export type TabId = "claims" | "evidence" | "timeline" | "compare" | "history";

interface Tab {
  id: TabId;
  label: string;
}

interface TabNavigationProps {
  activeTab: TabId;
  onChange: (tab: TabId) => void;
  counts?: Partial<Record<TabId, number>>;
  disabledTabs?: TabId[];
  showHistoryTab?: boolean;
}

const BASE_TABS: Tab[] = [
  { id: "claims", label: "Claims" },
  { id: "evidence", label: "Evidence" },
  { id: "timeline", label: "Timeline" },
  { id: "compare", label: "Compare" },
];

const HASH_TO_TAB: Record<string, TabId> = {
  claims: "claims",
  evidence: "evidence",
  timeline: "timeline",
  compare: "compare",
  history: "history",
};

function tabToHash(tab: TabId): string {
  return `#${tab}`;
}

export function TabNavigation({
  activeTab,
  onChange,
  counts = {},
  disabledTabs = [],
  showHistoryTab = false,
}: TabNavigationProps) {
  const tabRefs = useRef<Partial<Record<TabId, HTMLButtonElement | null>>>({});
  const hasAppliedHashRef = useRef(false);

  const tabs = useMemo<Tab[]>(() => {
    return showHistoryTab
      ? [...BASE_TABS, { id: "history", label: "History" }]
      : BASE_TABS;
  }, [showHistoryTab]);

  const enabledTabs = useMemo(() => {
    return tabs
      .map((tab) => tab.id)
      .filter((tabId) => !disabledTabs.includes(tabId));
  }, [tabs, disabledTabs]);

  useEffect(() => {
    if (hasAppliedHashRef.current) return;
    if (typeof window === "undefined") return;

    const rawHash = window.location.hash.replace(/^#/, "").toLowerCase();
    const hashTab = HASH_TO_TAB[rawHash];
    if (!hashTab) {
      hasAppliedHashRef.current = true;
      return;
    }

    if (!tabs.some((tab) => tab.id === hashTab)) {
      hasAppliedHashRef.current = true;
      return;
    }

    if (disabledTabs.includes(hashTab)) {
      hasAppliedHashRef.current = true;
      return;
    }

    if (hashTab !== activeTab) {
      onChange(hashTab);
    }

    hasAppliedHashRef.current = true;
  }, [activeTab, disabledTabs, onChange, tabs]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const nextHash = tabToHash(activeTab);
    if (window.location.hash === nextHash) return;
    window.history.replaceState(null, "", nextHash);
  }, [activeTab]);

  const handleArrowNavigation = (direction: "left" | "right") => {
    if (enabledTabs.length === 0) return;
    const activeIndex = enabledTabs.indexOf(activeTab);
    if (activeIndex === -1) {
      const fallbackTab = enabledTabs[0];
      onChange(fallbackTab);
      tabRefs.current[fallbackTab]?.focus();
      return;
    }

    const offset = direction === "right" ? 1 : -1;
    const nextIndex = (activeIndex + offset + enabledTabs.length) % enabledTabs.length;
    const nextTab = enabledTabs[nextIndex];

    onChange(nextTab);
    tabRefs.current[nextTab]?.focus();
  };

  return (
    <div className="w-full">
      <div
        role="tablist"
        aria-label="Result views"
        className="relative flex items-center border-b border-border overflow-x-auto"
        style={{ scrollbarWidth: "none" }}
      >
        {tabs.map((tab) => {
          const isActive   = tab.id === activeTab;
          const isDisabled = disabledTabs.includes(tab.id);
          const count      = counts[tab.id];

          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${tab.id}`}
              id={`tab-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              ref={(el) => {
                tabRefs.current[tab.id] = el;
              }}
              onClick={() => !isDisabled && onChange(tab.id)}
              onKeyDown={(event) => {
                if (event.key === "ArrowRight") {
                  event.preventDefault();
                  handleArrowNavigation("right");
                } else if (event.key === "ArrowLeft") {
                  event.preventDefault();
                  handleArrowNavigation("left");
                }
              }}
              disabled={isDisabled}
              className={`
                relative flex items-center gap-2 px-4 py-3 text-sm whitespace-nowrap border-b-2
                transition-colors duration-200 flex-shrink-0
                ${isActive
                  ? "text-accent font-semibold border-accent"
                  : isDisabled
                  ? "text-text-muted cursor-not-allowed opacity-40 border-transparent"
                  : "text-text-secondary hover:text-text-primary border-transparent"
                }
              `}
            >
              {tab.label}

              {/* Count badge */}
              {count !== undefined && count > 0 && (
                <span
                  className="inline-flex items-center justify-center min-w-[18px] h-[18px]
                             px-1 rounded-full text-xs leading-none"
                  style={
                    isActive
                      ? { background: "var(--color-accent-glow)", color: "var(--color-accent)", border: "1px solid var(--color-accent-dim)" }
                      : { background: "var(--color-surface-high)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }
                  }
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}