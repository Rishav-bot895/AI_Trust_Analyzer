import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { ClaimsTable } from "../ClaimsTable";
import type { Claim, Evidence } from "../../types/api";

const claimsFixture: Claim[] = [
  {
    id: "claim-1",
    text: "The Eiffel Tower is in Paris.",
    confidence: 0.9,
    status: "SUPPORTED",
    claimIndex: 0,
    sourceSpan: null,
  },
  {
    id: "claim-2",
    text: "The moon is made of cheese.",
    confidence: 0.2,
    status: "UNSUPPORTED",
    claimIndex: 1,
    sourceSpan: null,
  },
  {
    id: "claim-3",
    text: "Water boils at 50C at sea level.",
    confidence: 0.4,
    status: "CONTRADICTED",
    claimIndex: 2,
    sourceSpan: null,
  },
];

const evidenceFixture: Evidence[] = [
  {
    id: "ev-1",
    claimId: "claim-1",
    snippet: "Paris is the capital city of France.",
    sourceUrl: null,
    sourceTitle: null,
    relevanceScore: 0.95,
    sourceType: "WEB_SEARCH",
    polarity: "FOR",
    retrievedAt: "2025-01-01T00:00:00Z",
  },
  {
    id: "ev-2",
    claimId: "claim-1",
    snippet: "The Eiffel Tower stands on the Champ de Mars in Paris.",
    sourceUrl: null,
    sourceTitle: null,
    relevanceScore: 0.9,
    sourceType: "PGVECTOR",
    polarity: "FOR",
    retrievedAt: "2025-01-01T00:00:00Z",
  },
];

describe("ClaimsTable", () => {
  test("test_claims_table_renders_all_claims", () => {
    render(<ClaimsTable claims={claimsFixture} evidence={evidenceFixture} />);

    expect(screen.getByText("The Eiffel Tower is in Paris.")).toBeInTheDocument();
    expect(screen.getByText("The moon is made of cheese.")).toBeInTheDocument();
    expect(screen.getByText("Water boils at 50C at sea level.")).toBeInTheDocument();
  });

  test("test_claims_filter_by_status", async () => {
    const user = userEvent.setup();
    render(<ClaimsTable claims={claimsFixture} evidence={evidenceFixture} />);

    await user.click(screen.getByRole("button", { name: "Supported (1)" }));

    expect(screen.getByText("The Eiffel Tower is in Paris.")).toBeInTheDocument();
    expect(screen.queryByText("The moon is made of cheese.")).not.toBeInTheDocument();
    expect(screen.queryByText("Water boils at 50C at sea level.")).not.toBeInTheDocument();
  });

  test("test_claims_filter_by_contradicted_and_unsupported_status", async () => {
    const user = userEvent.setup();
    render(<ClaimsTable claims={claimsFixture} evidence={evidenceFixture} />);

    await user.click(screen.getByRole("button", { name: "Contradicted (1)" }));

    expect(screen.getByText("Water boils at 50C at sea level.")).toBeInTheDocument();
    expect(screen.queryByText("The Eiffel Tower is in Paris.")).not.toBeInTheDocument();
    expect(screen.queryByText("The moon is made of cheese.")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Unsupported (1)" }));

    expect(screen.getByText("The moon is made of cheese.")).toBeInTheDocument();
    expect(screen.queryByText("Water boils at 50C at sea level.")).not.toBeInTheDocument();
  });

  test("test_claims_expand_shows_evidence", async () => {
    const user = userEvent.setup();
    render(<ClaimsTable claims={claimsFixture} evidence={evidenceFixture} />);

    await user.click(screen.getByRole("button", { name: /The Eiffel Tower is in Paris\./ }));

    expect(screen.getByText("Evidence snippets")).toBeInTheDocument();
    expect(screen.getByText("Paris is the capital city of France.")).toBeInTheDocument();
    expect(
      screen.getByText("The Eiffel Tower stands on the Champ de Mars in Paris."),
    ).toBeInTheDocument();
  });

  test("test_claims_expand_without_evidence_shows_empty_detail", async () => {
    const user = userEvent.setup();
    render(<ClaimsTable claims={claimsFixture} evidence={evidenceFixture} />);

    await user.click(screen.getByRole("button", { name: /The moon is made of cheese\./ }));

    expect(screen.getByText("Evidence snippets")).toBeInTheDocument();
    expect(screen.getByText("No evidence snippets for this claim.")).toBeInTheDocument();
  });

  test("test_claims_sort_by_confidence", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ClaimsTable claims={claimsFixture} evidence={evidenceFixture} />,
    );

    const getRowOrder = () =>
      Array.from(container.querySelectorAll(".grid.w-full"))
        .map((row) => row.textContent ?? "")
        .join("\n");

    const initialOrder = getRowOrder();
    expect(initialOrder.indexOf("The Eiffel Tower is in Paris.")).toBeLessThan(
      initialOrder.indexOf("The moon is made of cheese."),
    );

    await user.click(screen.getByRole("button", { name: /Confidence/ }));

    const ascOrder = getRowOrder();
    expect(ascOrder.indexOf("The moon is made of cheese.")).toBeLessThan(
      ascOrder.indexOf("The Eiffel Tower is in Paris."),
    );
  });

  test("test_claims_filter_empty_result_message", async () => {
    const user = userEvent.setup();
    render(
      <ClaimsTable
        claims={[{ ...claimsFixture[0], status: "SUPPORTED" }]}
        evidence={evidenceFixture}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Contradicted (0)" }));

    expect(screen.getByText("No claims extracted")).toBeInTheDocument();
  });

  test("test_claims_empty_state_message", () => {
    render(<ClaimsTable claims={[]} evidence={[]} />);

    expect(screen.getByText("No claims extracted")).toBeInTheDocument();
  });

  test("test_claims_table_shows_skeleton_rows", () => {
    render(<ClaimsTable claims={[]} evidence={[]} isLoading />);

    expect(screen.getByLabelText("claims-table-skeleton")).toBeInTheDocument();
    expect(screen.getAllByLabelText("claim-row-skeleton")).toHaveLength(4);
    expect(screen.queryByText("No claims extracted")).not.toBeInTheDocument();
  });
});
