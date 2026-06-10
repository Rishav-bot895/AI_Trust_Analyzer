import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, test } from "vitest";
import { TabNavigation, type TabId } from "../TabNavigation";

function TabHarness(props?: {
  disabledTabs?: TabId[];
  showHistoryTab?: boolean;
}) {
  const [activeTab, setActiveTab] = useState<TabId>("claims");

  return (
    <TabNavigation
      activeTab={activeTab}
      onChange={setActiveTab}
      counts={{ claims: 3, evidence: 2, compare: 0 }}
      disabledTabs={props?.disabledTabs ?? []}
      showHistoryTab={props?.showHistoryTab ?? false}
    />
  );
}

describe("TabNavigation", () => {
  test("test_tab_click_changes_active", async () => {
    const user = userEvent.setup();
    render(<TabHarness />);

    const evidenceTab = screen.getByRole("tab", { name: /Evidence/i });
    await user.click(evidenceTab);

    expect(evidenceTab).toHaveAttribute("aria-selected", "true");
  });

  test("test_tab_hash_sync", async () => {
    const user = userEvent.setup();
    window.history.replaceState(null, "", "#timeline");

    render(<TabHarness />);

    expect(screen.getByRole("tab", { name: "Timeline" })).toHaveAttribute("aria-selected", "true");

    await user.click(screen.getByRole("tab", { name: /Claims/i }));

    expect(window.location.hash).toBe("#claims");
  });

  test("test_tab_keyboard_navigation", async () => {
    const user = userEvent.setup();
    render(<TabHarness />);

    const claimsTab = screen.getByRole("tab", { name: /Claims/i });
    claimsTab.focus();

    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("tab", { name: /Evidence/i })).toHaveAttribute("aria-selected", "true");
  });

  test("test_tab_disabled_compare_without_data", async () => {
    const user = userEvent.setup();
    window.history.replaceState(null, "", "#claims");
    render(<TabHarness disabledTabs={["compare"]} />);

    const compareTab = screen.getByRole("tab", { name: "Compare" });
    expect(compareTab).toBeDisabled();
    expect(compareTab).toHaveAttribute("aria-selected", "false");

    await user.click(compareTab);

    expect(compareTab).toHaveAttribute("aria-selected", "false");
  });
});
