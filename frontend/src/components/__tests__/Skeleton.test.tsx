import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { Skeleton, SkeletonCard, SkeletonRow } from "../Skeleton";

describe("Skeleton", () => {
  test("test_skeleton_renders_with_pulse", () => {
    render(<Skeleton width={120} height={24} className="custom-skeleton" />);

    const skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveClass("animate-pulse");
    expect(skeleton).toHaveClass("custom-skeleton");
    expect(skeleton).toHaveStyle({ width: "120px", height: "24px" });
  });

  test("test_skeleton_presets_render", () => {
    render(
      <>
        <SkeletonCard />
        <SkeletonRow />
      </>,
    );

    expect(screen.getByLabelText("evidence-card-skeleton")).toBeInTheDocument();
    expect(screen.getByLabelText("claim-row-skeleton")).toBeInTheDocument();
  });
});
