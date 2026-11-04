// SPDX-License-Identifier: Apache-2.0
// `room.tools` and `room.seats[].busy`: the agents' tool calls as the host recorded them, read so
// that a missing or malformed value becomes an empty one. Words for the screen live here too.

export type ToolStatus = "started" | "done" | "failed";
export type ToolCallItem = {
  /** The event id of the call's start (or of its only event). */
  id: string;
  at: string;
  seq: number;
  /** A participant id, or "host" for the host's own work. */
  seat: string;
  agent: string;
  /** `<family>:<name>`, for example `model:offer`, `mcp:make_offer`, `psi:compare`. */
  tool: string;
  args: string;
  result: string;
  status: ToolStatus;
  ms: number;
  refs: string[];
  ended: string | null;
};
export type Busy = { tool: string; args: string; since: string };

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => v !== null && typeof v === "object" && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === "string" ? v : "");
const num = (v: unknown): number =>
  typeof v === "number" && Number.isFinite(v) ? Math.max(0, v) : 0;

export function readTools(v: unknown): ToolCallItem[] {
  if (!Array.isArray(v)) return [];
  return v
    .filter(isRec)
    .filter((t) => str(t.id) !== "" && str(t.tool) !== "")
    .map((t) => ({
      id: str(t.id),
      at: str(t.at),
      seq: num(t.seq),
      seat: str(t.seat) || "host",
      agent: str(t.agent) || "host",
      tool: str(t.tool),
      args: str(t.args),
      result: str(t.result),
      status: t.status === "done" || t.status === "failed" ? t.status : "started",
      ms: num(t.ms),
      refs: Array.isArray(t.refs) ? t.refs.filter((r): r is string => typeof r === "string") : [],
      ended: str(t.ended) || null,
    }));
}

export function readBusy(v: unknown): Busy | null {
  if (!isRec(v) || str(v.tool) === "") return null;
  return { tool: str(v.tool), args: str(v.args), since: str(v.since) };
}

const FAMILIES: Record<string, string> = {
  model: "model call",
  psi: "private comparison",
  steward: "Steward",
  mcp: "MCP tool",
  a2a: "A2A message",
  search: "web search",
  media: "media",
  mint: "minted tool",
};

/** `mcp:make_offer` to `make offer`, and its family in words. */
export function toolWords(tool: string): { family: string; name: string } {
  const [family = "", name = ""] = tool.split(":");
  return { family: FAMILIES[family] ?? family, name: name.replaceAll("_", " ") };
}

export function seatName(seats: { seat: string; label: string }[], seat: string): string {
  if (seat === "host") return "Host";
  if (seat === "outside") return "An outside agent";
  return seats.find((s) => s.seat === seat)?.label ?? "A seat";
}

export function duration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`;
}
