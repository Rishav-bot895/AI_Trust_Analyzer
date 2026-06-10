"use client";

import { useState, useRef, useEffect } from "react";

export type TabId = "results" | "claims" | "evidence" | "timeline" | "comparison";

interface Tab {
  id: TabId;
  label: string;
  count?: number;
}

interface TabNavigationProps {
  activeTab: TabId;
  onChange: (tab: TabId) => void;
  counts?: Partial<Record<TabId, number>>;
  disabledTabs?: TabId[];
}

const TABS: Tab[] = [
  { id: "results",    label: "Results"    },
  { id: "claims",     label: "Claims"     },
  { id: "evidence",   label: "Evidence"   },
  { id: "timeline",   label: "Timeline"   },
  { id: "comparison", label: "Compare"    },
];

export function TabNavigation({
  activeTab,
  onChange,
  counts = {},
  disabledTabs = [],
}: TabNavigationProps) {
  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0 });
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  // Move the sliding indicator to the active tab
  useEffect(() => {
    const el = tabRefs.current[activeTab];
    if (!el) return;
    const parent = el.parentElement;
    if (!parent) return;
    const parentRect = parent.getBoundingClientRect();
    const elRect     = el.getBoundingClientRect();
    setIndicatorStyle({
      left:  elRect.left  - parentRect.left,
      width: elRect.width,
    });
  }, [activeTab]);

  return (
    <div className="w-full">
      <div
        className="relative flex items-center border-b border-border overflow-x-auto"
        style={{ scrollbarWidth: "none" }}
      >
        {/* Sliding underline indicator */}
        <div
          className="absolute bottom-0 h-0.5 transition-all duration-300 ease-out"
          style={{
            left:       indicatorStyle.left,
            width:      indicatorStyle.width,
            background: "var(--color-accent)",
            boxShadow:  "0 0 8px var(--color-accent)",
          }}
        />

        {TABS.map((tab) => {
          const isActive   = tab.id === activeTab;
          const isDisabled = disabledTabs.includes(tab.id);
          const count      = counts[tab.id];

          return (
            <button
              key={tab.id}
              type="button"
              ref={(el) => { tabRefs.current[tab.id] = el; }}
              onClick={() => !isDisabled && onChange(tab.id)}
              disabled={isDisabled}
              className={`
                relative flex items-center gap-2 px-4 py-3 text-sm whitespace-nowrap
                transition-colors duration-200 flex-shrink-0
                ${isActive
                  ? "text-accent"
                  : isDisabled
                  ? "text-text-muted cursor-not-allowed opacity-40"
                  : "text-text-secondary hover:text-text-primary"
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