// SPDX-License-Identifier: Apache-2.0
// The MCP App view draws the structured content of a tool result with the same catalog the room
// uses. These functions turn that content into A2UI messages. Nothing here reads a Coalition ID
// from the address: it arrives as tool data.
import { CATALOG_ID } from "../catalog";
import type { ViewerState } from "../feed/delta";
import { deriveRoom, fixedFields } from "../feed/derive";

const VERSION = "v0.9" as const;
export const SURFACE_ID = "mcp";

type Json = Record<string, unknown>;
export type McpEvent = { seq?: number; type?: string; payload?: unknown };
export type McpTask = { task_id?: string; title?: string; status?: string };
export type McpQuestion = { query_id?: string; kind?: string; subject?: string };
export type McpDecision = {
  subject?: { kind?: string; id?: string; revision?: number };
  prompt?: string;
};
export type McpSurface = {
  title?: string;
  status?: string;
  tasks?: McpTask[];
  questions?: McpQuestion[];
  decisions?: McpDecision[];
  events?: McpEvent[];
};
export type McpSummary = { coalition_id?: string; goal?: string; status?: string };

/** What a tool result can carry for this view: my_view, pending_questions or list_coalitions. */
export type McpData = {
  coalition_id?: string;
  device?: string;
  surface?: McpSurface;
  questions?: McpQuestion[];
  coalitions?: McpSummary[];
};

export function parseData(value: unknown): McpData | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as McpData;
}

const TASK_STATUS = new Set([
  "open",
  "negotiating",
  "proposed",
  "decided",
  "committed",
  "done",
  "withdrawn",
]);

/** The viewer projection the room reads, rebuilt from the event list the tool result carries. */
export function viewerStateOf(data: McpData): ViewerState {
  const events: Json = {};
  for (const [n, e] of (data.surface?.events ?? []).entries()) {
    events[`e${e.seq ?? n}`] = { type: e.type ?? "", seq: e.seq ?? n, payload: e.payload ?? {} };
  }
  return { coalition_id: data.coalition_id ?? "", events };
}

const text = (v: unknown, fallback = "") => (typeof v === "string" && v ? v : fallback);

type Component = Json & { id: string; component: string };

/** Components and data for one my_view result. The root is a Column holding everything. */
export function surfaceParts(data: McpData): { components: Component[]; model: Json } {
  const surface = data.surface ?? {};
  const state = viewerStateOf(data);
  const room = deriveRoom(state);
  const title = text(surface.title, room.title);
  const components: Component[] = [];
  const ids: string[] = ["head", "fixed"];
  components.push(
    { id: "head", component: "Heading", text: { path: "/title" }, variant: "h2" },
    { id: "fixed", component: "Card", title: "Standard view", fields: { path: "/fields" } },
  );
  for (const [i, t] of (surface.tasks ?? []).entries()) {
    const id = `task-${i}`;
    ids.push(id);
    components.push({
      id,
      component: "TaskCard",
      task_id: text(t.task_id, id),
      title: text(t.title, "Task"),
      status: TASK_STATUS.has(t.status ?? "") ? t.status : "open",
    });
  }
  for (const [i, q] of (surface.questions ?? []).entries()) {
    const id = `q-${i}`;
    ids.push(id);
    components.push({
      id,
      component: "Card",
      tone: "ask",
      title: `Question: ${text(q.kind, "open")}`,
      fields: [{ label: "About", value: text(q.subject, text(q.query_id, "-")) }],
    });
  }
  for (const [i, d] of (surface.decisions ?? []).entries()) {
    const id = `d-${i}`;
    ids.push(id);
    const s = d.subject ?? {};
    components.push(
      {
        id,
        component: "Card",
        tone: "ask",
        title: text(d.prompt, "A decision waits for you"),
        children: [`${id}-go`],
      },
      {
        id: `${id}-go`,
        component: "Button",
        label: "Review and decide",
        variant: "primary",
        action: {
          event: {
            name: "decide",
            context: { kind: text(s.kind), id: text(s.id), revision: String(s.revision ?? "") },
          },
        },
      },
    );
  }
  components.push({ id: "root", component: "Column", gap: "12", children: ids });
  return { components, model: { title, fields: fixedFields(state) } };
}

/** The Coalitions a person belongs to, as cards with one button each. */
export function pickerParts(list: McpSummary[]): { components: Component[]; model: Json } {
  const ids: string[] = ["head"];
  const components: Component[] = [
    { id: "head", component: "Heading", text: "Your Coalitions", variant: "h2" },
  ];
  for (const [i, c] of list.entries()) {
    const id = `c-${i}`;
    ids.push(id);
    components.push(
      {
        id,
        component: "Card",
        title: text(c.goal, "Coalition"),
        children: [`${id}-open`],
      },
      {
        id: `${id}-open`,
        component: "Button",
        label: "Open",
        variant: "secondary",
        action: { event: { name: "open", context: { coalition_id: text(c.coalition_id) } } },
      },
    );
  }
  components.push({ id: "root", component: "Column", gap: "12", children: ids });
  return { components, model: {} };
}

/** A2UI messages. Only the first set creates the surface; later ones update it in place. */
export function messagesFor(
  parts: { components: unknown[]; model: unknown },
  first: boolean,
): unknown[] {
  const out: unknown[] = [];
  if (first) {
    out.push({ version: VERSION, createSurface: { surfaceId: SURFACE_ID, catalogId: CATALOG_ID } });
  }
  out.push(
    { version: VERSION, updateComponents: { surfaceId: SURFACE_ID, components: parts.components } },
    { version: VERSION, updateDataModel: { surfaceId: SURFACE_ID, path: "/", value: parts.model } },
  );
  return out;
}

/** The tool that records a decision, and its arguments. The view never sends a consent flag. */
export function decisionCall(
  coalitionId: string,
  ctx: { kind?: string; id?: string; revision?: string },
): { name: string; arguments: Json } | null {
  const kind = text(ctx.kind);
  const id = text(ctx.id);
  if (!kind || !id) return null;
  if (kind === "commitment") {
    return {
      name: "approve_commitment",
      arguments: { coalition_id: coalitionId, commitment_id: id },
    };
  }
  if (kind === "charter")
    return { name: "accept_charter", arguments: { coalition_id: coalitionId } };
  const revision = Number(ctx.revision);
  if (!Number.isInteger(revision) || revision < 1) return null;
  return {
    name: "decide",
    arguments: { coalition_id: coalitionId, subject: { kind, id, revision }, choice: id },
  };
}
