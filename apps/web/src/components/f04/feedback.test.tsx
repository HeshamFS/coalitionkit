// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { FeedbackForm } from "./feedback";

afterEach(cleanup);

it("saves only the answers the member entered and keeps the default audience private", () => {
  const send = vi.fn();
  render(
    <FeedbackForm
      p={{
        questions: [
          {
            id: "goal",
            kind: "choice",
            label: "Goal reached?",
            options: [{ id: "yes", label: "Yes" }],
          },
          { id: "fair", kind: "scale", label: "Fair?" },
          { id: "lesson", kind: "text", label: "Lesson" },
        ],
      }}
      send={send}
    />,
  );
  expect(screen.getByRole("button", { name: "Yes" })).toHaveAttribute("aria-pressed", "false");
  fireEvent.click(screen.getByRole("button", { name: "Yes" }));
  fireEvent.click(screen.getByRole("button", { name: "4" }));
  fireEvent.change(screen.getByLabelText(/Lesson/), { target: { value: "Ask sooner" } });
  fireEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("feedback.save", {
    values: { goal: "yes", fair: "4", lesson: "Ask sooner" },
    audience: "me",
  });
});
