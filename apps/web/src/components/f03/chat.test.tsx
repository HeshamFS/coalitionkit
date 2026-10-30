// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AgentStatus, Message, ToolCall } from "./chat";

afterEach(cleanup);

it("keeps hidden message contents out of the DOM and exposes only length hints", () => {
  const { container } = render(
    <Message
      p={{
        state: "redacted",
        text: "secret text",
        redactions: [{ length: { value: 10, event_ref: "e1" } }],
      }}
      send={vi.fn()}
    />,
  );
  expect(container).not.toHaveTextContent("secret text");
  expect(screen.getByRole("img", { name: "Redacted content" })).toBeVisible();
  expect(container.querySelector(".f03-redaction")).toHaveStyle({ width: "70px" });
});

it("does not expose blocked content and retries a failed message", () => {
  const send = vi.fn();
  const { rerender } = render(
    <Message
      p={{ state: "blocked", text: "secret text", policy: "no-regulated-advice" }}
      send={send}
    />,
  );
  expect(screen.queryByText("secret text")).toBeNull();
  expect(screen.getByText("Blocked by the steward: regulated advice")).toBeVisible();
  expect(screen.queryByRole("button")).toBeNull();
  rerender(<Message p={{ state: "failed", text: "Public text" }} send={send} />);
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("message.retry");
});

it("keeps tool arguments collapsed until the viewer expands the call", () => {
  const send = vi.fn();
  render(
    <ToolCall
      p={{ state: "done", tool: "view.read", summary: "View ready", args: { scope: "task:t2" } }}
      send={send}
    />,
  );
  expect(screen.queryByText(/task:t2/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Show the call ▾" }));
  expect(screen.getByText(/task:t2/)).toBeVisible();
  expect(send).toHaveBeenCalledExactlyOnceWith("toolcall.expand");
});

it("resumes a paused agent through its status card", () => {
  const send = vi.fn();
  render(<AgentStatus p={{ state: "paused", task: "Paused at 21:58" }} send={send} />);
  fireEvent.click(screen.getByRole("button", { name: "Resume" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("agent.resume");
});
