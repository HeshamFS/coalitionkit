// SPDX-License-Identifier: Apache-2.0
import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Bridge, ToolResult } from "./bridge";
import { McpView } from "./McpView";
import { decisionCall } from "./surface";

const COALITION = "01M4XRC000000G40R40M30E209";

const events = (n: number) =>
  Array.from({ length: n }, (_, i) => ({
    seq: i + 1,
    type: i === 0 ? "coalition.charter" : "coalition.join",
    payload: i === 0 ? { goal: "Goal 1" } : {},
  }));

const myView = (surface: object): ToolResult => ({
  structuredContent: { coalition_id: COALITION, device: "mcp-app", surface },
  content: [{ type: "text", text: "Goal 1" }],
});

/** A bridge the test drives: `push` plays the host passing a tool result in. */
function fakeBridge(initial: ToolResult, polled: () => ToolResult) {
  let listener: (r: ToolResult) => void = () => {};
  const calls: { name: string; args: Record<string, unknown> }[] = [];
  const bridge: Bridge = {
    onToolResult(l) {
      listener = l;
      l(initial);
    },
    onTheme: () => {},
    callTool: vi.fn(async (name: string, args: Record<string, unknown>) => {
      calls.push({ name, args });
      return name === "my_view"
        ? polled()
        : { content: [{ type: "text", text: "Decision recorded." }] };
    }),
  };
  return { bridge, calls, push: (r: ToolResult) => listener(r) };
}

describe("the MCP App view", () => {
  it("draws the tool result with the catalog components", async () => {
    const result = myView({
      title: "Goal 1",
      events: events(3),
      tasks: [{ task_id: "t1", title: "Task 1", status: "decided" }],
    });
    const { bridge } = fakeBridge(result, () => result);
    render(<McpView bridge={bridge} pollMs={50} />);
    expect(await screen.findByRole("heading", { name: "Goal 1" })).toBeInTheDocument();
    expect(screen.getByText("Standard view")).toBeInTheDocument();
    expect(screen.getByText("Log entries").nextSibling).toHaveTextContent("3");
    expect(screen.getByRole("article", { name: "Task Task 1, decided" })).toBeInTheDocument();
  });

  it("refreshes by calling my_view through the bridge and shows the change", async () => {
    let n = 3;
    const first = myView({ events: events(3) });
    const { bridge, calls } = fakeBridge(first, () => myView({ events: events(n) }));
    render(<McpView bridge={bridge} pollMs={30} />);
    await screen.findByText("Log entries");
    expect(screen.getByText("Log entries").nextSibling).toHaveTextContent("3");
    n = 4;
    await waitFor(() => expect(screen.getByText("Log entries").nextSibling).toHaveTextContent("4"));
    expect(calls.every((c) => c.name === "my_view")).toBe(true);
    expect(calls[0]?.args).toEqual({ coalition_id: COALITION, device: "mcp-app" });
  });

  it("asks for a decision only through the tool whose elicitation the server owns", async () => {
    const withDecision = myView({
      events: events(2),
      decisions: [{ subject: { kind: "plan", id: "p1", revision: 2 }, prompt: "Take Plan A?" }],
    });
    const { bridge, calls } = fakeBridge(withDecision, () => withDecision);
    const user = userEvent.setup();
    render(<McpView bridge={bridge} pollMs={500} />);
    await user.click(await screen.findByRole("button", { name: "Review and decide" }));
    await waitFor(() => expect(calls.some((c) => c.name === "decide")).toBe(true));
    const sent = calls.find((c) => c.name === "decide");
    expect(sent?.args).toEqual({
      coalition_id: COALITION,
      subject: { kind: "plan", id: "p1", revision: 2 },
      choice: "p1",
    });
    expect(JSON.stringify(sent)).not.toMatch(/consent|confirmed/);
    expect(await screen.findByText(/Decision recorded/)).toBeInTheDocument();
  });

  it("shows a refusal from the host as text", async () => {
    const { bridge } = fakeBridge(
      { isError: true, content: [{ type: "text", text: "unknown_participant: no" }] },
      () => ({ isError: true }),
    );
    render(<McpView bridge={bridge} pollMs={50} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("unknown_participant");
  });

  it("offers a choice when the host lists several Coalitions", async () => {
    const listed: ToolResult = {
      structuredContent: {
        coalitions: [
          { coalition_id: COALITION, goal: "Goal 1" },
          { coalition_id: "01M4XRC1J00000000000000000", goal: "Goal 2" },
        ],
      },
    };
    const { bridge, calls } = fakeBridge(listed, () => myView({ events: events(2) }));
    const user = userEvent.setup();
    render(<McpView bridge={bridge} pollMs={500} />);
    const buttons = await screen.findAllByRole("button", { name: "Open" });
    expect(buttons).toHaveLength(2);
    await user.click(buttons[1] as HTMLElement);
    await waitFor(() => expect(calls[0]?.args.coalition_id).toBe("01M4XRC1J00000000000000000"));
  });
});

describe("decisionCall", () => {
  it("maps each subject to the tool that owns its question and never sends consent", () => {
    expect(decisionCall("c", { kind: "charter", id: "c" })?.name).toBe("accept_charter");
    expect(decisionCall("c", { kind: "commitment", id: "k1" })).toEqual({
      name: "approve_commitment",
      arguments: { coalition_id: "c", commitment_id: "k1" },
    });
    expect(decisionCall("c", { kind: "plan", id: "p1", revision: "x" })).toBeNull();
    expect(decisionCall("c", { kind: "", id: "p1", revision: "1" })).toBeNull();
  });
});

describe("the bundled view file", () => {
  const file = join(
    process.cwd(),
    "..",
    "..",
    "packages",
    "mcp_server",
    "src",
    "coalitionkit_mcp",
    "assets",
    "surface-v1.html",
  );

  it("is one file under 1.5 MB", () => {
    expect(statSync(file).size).toBeLessThan(1_500_000);
  });

  it("asks for nothing: no linked script, style, image or font; the closed policy is set", () => {
    const html = readFileSync(file, "utf8");
    expect(html).not.toMatch(/<script[^>]*\ssrc=/i);
    expect(html).not.toMatch(/<link\b/i);
    expect(html).not.toMatch(/<(img|iframe|video|audio|source|embed|object)\b[^>]*\ssrc=/i);
    expect(html).not.toMatch(/@import|url\(\s*["']?https?:/i);
    const policy = /http-equiv="Content-Security-Policy"\s+content="([^"]*)"/.exec(html)?.[1];
    expect(policy).toBe(
      "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'",
    );
    expect(html).not.toMatch(/\b[0-9A-HJKMNP-TV-Z]{26}\b/); // no Coalition ID in the file
  });
});
