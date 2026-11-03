// SPDX-License-Identifier: Apache-2.0
// The four room routes and the view-as read, all with the viewer token and nothing else. They act
// only for the signed-in viewer; a consent never goes through here (that is `answer`).
import { assertAllowedBase, type HostConfig, readConfig } from "../feed/config";
import type { Fetch } from "../feed/connection";

export type Call<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; error: string; detail: string; auth: boolean };

export type SayReply = {
  route: "private" | "room" | "change" | "other";
  reply: string;
  event_id?: string;
  stopped?: boolean;
};

async function request<T>(
  config: HostConfig | null,
  method: "GET" | "POST",
  path: string,
  body: unknown,
  fetchFn: Fetch,
): Promise<Call<T>> {
  if (!config) return { ok: false, status: 401, error: "no_session", detail: "", auth: true };
  assertAllowedBase(config.baseUrl);
  const headers: Record<string, string> = { Authorization: `Bearer ${config.token}` };
  if (method === "POST") headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetchFn(`${config.baseUrl}${path}`, {
      method,
      headers,
      body: method === "POST" ? JSON.stringify(body) : undefined,
    });
  } catch {
    return { ok: false, status: 0, error: "unreachable", detail: "", auth: false };
  }
  const json = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (res.ok) return { ok: true, data: json as T };
  const detail = typeof json.detail === "string" ? json.detail : "";
  return {
    ok: false,
    status: res.status,
    error: typeof json.error === "string" ? json.error : String(res.status),
    detail,
    auth: res.status === 401,
  };
}

export type RoomIo = {
  begin: (helpers: boolean) => Promise<Call<{ phase?: string }>>;
  brief: (
    questionId: string,
    answer: { value: unknown } | { skip: true },
  ) => Promise<Call<{ status?: string }>>;
  say: (text: string) => Promise<Call<SayReply>>;
  done: (taskId: string) => Promise<Call<{ seq?: number }>>;
  viewAs: (participant: string) => Promise<Call<{ messages: unknown[] }>>;
};

const routeOf = (v: unknown): SayReply["route"] =>
  v === "private" || v === "room" || v === "change" ? v : "other";

/** The routes against the real host. The token is read when a call is made, never kept here. */
export function liveIo(
  fetchFn: Fetch = (url, init) => fetch(url, init),
  config: () => HostConfig | null = () => readConfig(),
): RoomIo {
  return {
    begin: (helpers) => request(config(), "POST", "/v1/room/begin", { helpers }, fetchFn),
    brief: (question_id, answer) =>
      request(config(), "POST", "/v1/room/brief", { question_id, ...answer }, fetchFn),
    say: async (text) => {
      const r = await request<Record<string, unknown>>(
        config(),
        "POST",
        "/v1/room/say",
        { text },
        fetchFn,
      );
      if (!r.ok) return r;
      const d = r.data;
      return {
        ok: true,
        data: {
          route: routeOf(d.route),
          reply: typeof d.reply === "string" ? d.reply : "",
          event_id: typeof d.event_id === "string" ? d.event_id : undefined,
          stopped: d.stopped === true,
        },
      };
    },
    done: (task_id) => request(config(), "POST", "/v1/room/done", { task_id }, fetchFn),
    viewAs: (participant) =>
      request(
        config(),
        "GET",
        `/v1/view-as?participant=${encodeURIComponent(participant)}`,
        undefined,
        fetchFn,
      ),
  };
}

/** The words for a refused or failed call, from what the host said. */
export function problemText(r: Extract<Call<unknown>, { ok: false }>): string {
  if (r.status === 0) return "The host could not be reached. Nothing was sent.";
  if (r.detail) return `The host did not take that: ${r.detail}`;
  return `The host did not take that (${r.error}).`;
}
