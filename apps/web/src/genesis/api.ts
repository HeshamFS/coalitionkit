// SPDX-License-Identifier: Apache-2.0
// Genesis on the host: draft a coalition from a sentence, start it, invite, join.
// Contract: docs/ux/journey.md (S1). Requests go only to the allowed base (feed/config.ts).

import { assertAllowedBase, resolveBase } from "../feed/config";

export type Role = { id: string; label: string; count?: number };
export type Draft = {
  goal: string;
  roles: Role[];
  needs: string[];
  deadline: string | null;
  deciders: "all" | string[];
  pack: string | null;
};
export type ReadingKind = "role" | "need" | "deadline" | "count";
export type Reading = { span: [number, number]; kind: ReadingKind };
export type DraftReply = { draft: Draft; source: "reader" | "model"; reading: Reading[] };
export type Started = { coalition_id: string; owner: { participant: string; token: string } };
export type Invitation = { id: string; kind: "member" | "business"; link: string };
export type Joined = { coalition_id: string; participant: string; token: string };

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
      detail = typeof j.detail === "string" ? j.detail : "";
    } catch {
      detail = "";
    }
    throw new HostError(res.status, detail);
  }
  return (await res.json()) as T;
}

const defaultFetch: Fetch = (url, init) => fetch(url, init);

export function draftGoal(goal: string, signal?: AbortSignal, fetchFn = defaultFetch) {
  // Day words ("tonight", "by Friday") are read in the writer's own time zone.
  const utc_offset_minutes = -new Date().getTimezoneOffset();
  return post<DraftReply>(
    "/v1/genesis/draft",
    { goal, utc_offset_minutes },
    undefined,
    fetchFn,
    signal,
  );
}

export function startCoalition(draft: Draft, startCode: string, fetchFn = defaultFetch) {
  return post<Started>("/v1/genesis/start", { draft }, `Start ${startCode}`, fetchFn);
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
