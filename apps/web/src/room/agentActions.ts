// SPDX-License-Identifier: Apache-2.0
// A person acting through their own hosted agent: an offer the agent signs and sends as a normal
// member message, and private values kept in their own vault (never in the log or any screen).
import { assertAllowedBase, readConfig } from "../feed/config";
import type { Values } from "./extSchema";

type Fetch = (url: string, init: RequestInit) => Promise<Response>;

export class ActionError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail || `the host answered ${status}`);
  }
}

async function call<T>(
  method: "GET" | "POST",
  path: string,
  body: unknown,
  fetchFn: Fetch,
): Promise<T> {
  const config = readConfig();
  if (!config) throw new ActionError(401, "not signed in");
  assertAllowedBase(config.baseUrl);
  const res = await fetchFn(`${config.baseUrl}${path}`, {
    method,
    headers: {
      authorization: `Bearer ${config.token}`,
      ...(method === "POST" ? { "content-type": "application/json" } : {}),
    },
    body: method === "POST" ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = "";
    try {
      const j = (await res.json()) as { detail?: unknown; error?: unknown };
      detail = String(j.detail ?? j.error ?? "");
    } catch {
      detail = "";
    }
    throw new ActionError(res.status, detail);
  }
  return (await res.json()) as T;
}

const defaultFetch: Fetch = (url, init) => fetch(url, init);

export function sendOffer(needId: string, ext: Values, fetchFn = defaultFetch) {
  return call<{ seq?: number; offer_id?: string }>(
    "POST",
    "/v1/agent/offer",
    Object.keys(ext).length ? { need_id: needId, ext } : { need_id: needId },
    fetchFn,
  );
}

export function saveVault(values: Values, fetchFn = defaultFetch) {
  return call<unknown>("POST", "/v1/agent/vault", { values }, fetchFn);
}

export function vaultKeys(fetchFn = defaultFetch) {
  return call<{ keys?: string[] }>("GET", "/v1/agent/vault", undefined, fetchFn);
}
