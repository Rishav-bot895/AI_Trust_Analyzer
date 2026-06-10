import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { AuthGate } from "../AuthGate";

describe("AuthGate", () => {
  test("test_helper_text_renders_apostrophes_not_entities", () => {
    render(
      <AuthGate
        onAuthenticated={vi.fn()}
        onGuest={vi.fn()}
      />,
    );

    expect(screen.getByText("If the account exists, we'll log you in.")).toBeInTheDocument();
    expect(screen.queryByText(/&apos;/)).not.toBeInTheDocument();
  });

  test("test_password_visibility_toggle_switches_input_type", async () => {
    const user = userEvent.setup();

    render(
      <AuthGate
        onAuthenticated={vi.fn()}
        onGuest={vi.fn()}
      />,
    );

    const password = screen.getByPlaceholderText("Enter your password") as HTMLInputElement;
    expect(password.type).toBe("password");

    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(password.type).toBe("text");

    await user.click(screen.getByRole("button", { name: "Hide password" }));
    expect(password.type).toBe("password");
  });
});
