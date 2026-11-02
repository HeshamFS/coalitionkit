// SPDX-License-Identifier: Apache-2.0
// Genesis on the host: draft a coalition from a sentence, start it, invite, join.
// Contract: docs/ux/journey.md (S1). Requests go only to the allowed base (feed/config.ts).

import { assertAllowedBase, resolveBase } from "../feed/config";
import type { CleanupReport } from "../moments/Dissolve";

export type PackRef = { name: string; version: string };
/** What GET /v1/packs says of an installed pack. */
export type PackInfo = PackRef & {
  label?: string;
  roles: Record<string, { label?: string; may: string[] }>;
  vocabulary: Record<string, string | { one: string; other: string }>;
};
export type Suggestion = PackRef & { why: string[] };
export type Role = { id: string; label: string; count?: number };
export type Draft = {
  goal: string;
  roles: Role[];
  needs: string[];
  deadline: string | null;
  deciders: "all" | string[];
  pack: PackRef | null;
  place?: string | null;
};
export type ReadingKind = "role" | "need" | "deadline" | "count" | "place";
export type Reading = { span: [number, number]; kind: ReadingKind };
export type CardSize = "hero" | "wide" | "half" | "third";
/** One component the host chose for this sentence from the closed catalog. */
export type Card = {
  id: string;
  component: string;
  title: string;
  word: string | null;
  size: CardSize;
  props: Record<string, unknown>;
};
export type DraftReply = {
  composition?: { source: "reader" | "model"; cards: Card[] };
  draft: Draft;
  source: "reader" | "model";
  reading: Reading[];
  /** The pack the host would offer for this sentence; never bound without a choice. */
  suggested?: Suggestion | null;
  /** The chosen pack's words, when a pack was chosen. */
  vocabulary?: PackInfo["vocabulary"];
};
export type HostKey = { kty: string; crv: string; x: string; kid?: string };
export type Visibility = "code" | "nearby";
export type AgentHome = "hosted" | "whatsapp" | "mcp" | "a2a";
export type Arrival = {
  participant: string;
  role: string;
  label: string;
  home: AgentHome;
  at: string;
};
export type DoorState = {
  code: string;
  link: string;
  stopped: boolean;
  visibility: Visibility;
  goal: string;
  place: string | null;
  closes_at: string;
  seats: number;
  filled: number;
  arrivals: Arrival[];
  knocks: { id: string; at: string }[];
};
export type DoorCard = {
  goal: string;
  place: string | null;
  closes_at: string;
  seats: number;
  filled: number;
  roles: { id: string; label: string; open: number }[];
};
export type Started = {
  coalition_id: string;
  owner: { participant: string; token: string };
  host_key?: HostKey;
  door?: DoorState;
};
export type Invitation = { id: string; kind: "member" | "business"; link: string };
export type Joined = {
  coalition_id: string;
  participant: string;
  token: string;
  host_key?: HostKey;
};

export class HostError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail || `host answered ${status}`);
  }
}

type Fetch = (url: string, init: RequestInit) => Promise<Response>;

function base(): string {
  const b = resolveBase(globalThis.location?.search ?? "", import.meta.env);
  assertAllowedBase(b);
  return b;
}

async function post<T>(
  path: string,
  body: unknown,
  auth: string | undefined,
  fetchFn: Fetch,
  signal?: AbortSignal,
  soft?: (status: number, body: unknown) => T | undefined,
): Promise<T> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (auth) headers.authorization = auth;
  const res = await fetchFn(`${base()}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    let detail = "";
    try {
      const j = (await res.json()) as { detail?: unknown };
      const kept = soft?.(res.status, j);
      if (kept !== undefined) return kept;
      detail = typeof j.detail === "string" ? j.detail : "";
    } catch {
      detail = "";
    }
    throw new HostError(res.status, detail);
  }
  return (await res.json()) as T;
}

const defaultFetch: Fetch = (url, init) => fetch(url, init);

export async function listPacks(fetchFn = defaultFetch, signal?: AbortSignal): Promise<PackInfo[]> {
  const res = await fetchFn(`${base()}/v1/packs`, { method: "GET", signal });
  if (!res.ok) throw new HostError(res.status, "");
  const body: unknown = await res.json();
  return Array.isArray(body) ? (body as PackInfo[]) : [];
}

export function draftGoal(
  goal: string,
  signal?: AbortSignal,
  fetchFn = defaultFetch,
  pack: PackRef | null = null,
) {
  // Day words ("tonight", "by Friday") are read in the writer's own time zone.
  const utc_offset_minutes = -new Date().getTimezoneOffset();
  return post<DraftReply>(
    "/v1/genesis/draft",
    pack ? { goal, utc_offset_minutes, pack } : { goal, utc_offset_minutes },
    undefined,
    fetchFn,
    signal,
  );
}

/** Open a room. A start code is sent only if this tab holds one; a local host needs none. */
export function openRoom(
  draft: Draft,
  visibility: Visibility,
  startCode = "",
  fetchFn = defaultFetch,
) {
  return post<Started>(
    "/v1/genesis/start",
    { draft, visibility },
    startCode ? `Start ${startCode}` : undefined,
    fetchFn,
  );
}

async function read<T>(path: string, auth: string | undefined, fetchFn: Fetch): Promise<T> {
  const res = await fetchFn(`${base()}${path}`, {
    method: "GET",
    headers: auth ? { authorization: auth } : {},
  });
  if (!res.ok) throw new HostError(res.status, "");
  return (await res.json()) as T;
}

export function readDoor(ownerToken: string, fetchFn = defaultFetch) {
  return read<DoorState>("/v1/coalition/door", `Bearer ${ownerToken}`, fetchFn);
}

export function stopDoor(ownerToken: string, fetchFn = defaultFetch) {
  return post<DoorState>("/v1/coalition/door/stop", {}, `Bearer ${ownerToken}`, fetchFn);
}

export function answerKnock(
  ownerToken: string,
  id: string,
  answer: "yes" | "no",
  fetchFn = defaultFetch,
) {
  return post<DoorState>(
    `/v1/coalition/door/knocks/${encodeURIComponent(id)}`,
    { answer },
    `Bearer ${ownerToken}`,
    fetchFn,
  );
}

export function readDoorCard(code: string, fetchFn = defaultFetch) {
  return read<DoorCard>(`/v1/door/${encodeURIComponent(code)}`, undefined, fetchFn);
}

export function joinByCode(
  code: string,
  displayName: string,
  role: string,
  fetchFn = defaultFetch,
) {
  const name = displayName.trim();
  return post<Joined>(
    "/v1/door/join",
    { code, ...(name ? { display_name: name } : {}), ...(role ? { role } : {}) },
    undefined,
    fetchFn,
  );
}

export function knockAt(room: string, fetchFn = defaultFetch) {
  return post<{ knock: string; secret: string }>(
    `/v1/rooms/${encodeURIComponent(room)}/knock`,
    {},
    undefined,
    fetchFn,
  );
}

export function readKnock(room: string, knock: string, secret: string, fetchFn = defaultFetch) {
  return read<{ state: "waiting" | "yes" | "no"; invitation?: string }>(
    `/v1/rooms/${encodeURIComponent(room)}/knocks/${encodeURIComponent(knock)}?secret=${encodeURIComponent(secret)}`,
    undefined,
    fetchFn,
  );
}

export function invite(
  ownerToken: string,
  kind: Invitation["kind"],
  count = 1,
  fetchFn = defaultFetch,
) {
  return post<{ invitations: Invitation[] }>(
    "/v1/invitations",
    { kind, count },
    `Bearer ${ownerToken}`,
    fetchFn,
  );
}

export function acceptInvitation(invitation: string, displayName: string, fetchFn = defaultFetch) {
  const body = displayName.trim()
    ? { invitation, display_name: displayName.trim() }
    : { invitation };
  return post<Joined>("/v1/invitations/accept", body, undefined, fetchFn);
}

/**
 * End the coalition for everyone. Resolves with the host's counts, or with `{failed, done}` when a
 * cleanup step failed (the host answers 500 and a retry is safe).
 */
export function dissolveCoalition(
  ownerToken: string,
  reason: "completed" | "cancelled",
  fetchFn = defaultFetch,
): Promise<CleanupReport> {
  return post<CleanupReport>(
    "/v1/coalition/dissolve",
    { reason },
    `Bearer ${ownerToken}`,
    fetchFn,
    undefined,
    (status, body) => {
      const b = body as { failed?: unknown };
      return status === 500 && typeof b.failed === "string" ? (body as CleanupReport) : undefined;
    },
  );
}
