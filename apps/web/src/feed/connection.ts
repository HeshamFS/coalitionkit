// SPDX-License-Identifier: Apache-2.0
import { runHttpRequest, transformHttpEventStream } from "@ag-ui/client";
import { assertAllowedBase, type HostConfig } from "./config";
import type { FeedEvent } from "./store";

export type Fetch = (url: string, init: RequestInit) => Promise<Response>;

export type StreamOptions = {
  config: HostConfig;
  path: "/v1/feed" | "/v1/agent";
  /** Return false to drop the stream and reopen it with a fresh run. */
  onEvent: (event: FeedEvent) => boolean;
  onStatus: (status: "live" | "reconnecting") => void;
  /** The host refused the token (401 or 403). The stream stops for good instead of retrying. */
  onAuthError?: () => void;
  fetchFn?: Fetch;
  /** Delay before reconnect number `attempt` (0-based), in ms. */
  delay?: (attempt: number) => number;
};

export const isAuthFailure = (status: number) => status === 401 || status === 403;

export const backoff = (attempt: number) => Math.min(15_000, 1000 * 2 ** attempt);

/**
 * One long-lived SSE stream. It reads events with the AG-UI client parser, and when the stream
 * ends or errors it opens a fresh run (the host sends a new snapshot) after a pause.
 */
export function openStream(opts: StreamOptions): () => void {
  assertAllowedBase(opts.config.baseUrl);
  const fetchFn: Fetch = opts.fetchFn ?? ((url, init) => fetch(url, init));
  const delay = opts.delay ?? backoff;
  let stopped = false;
  let attempt = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let abort: AbortController | undefined;
  let unsubscribe: (() => void) | undefined;

  const retry = () => {
    unsubscribe?.();
    abort?.abort();
    if (stopped) return;
    opts.onStatus("reconnecting");
    timer = setTimeout(connect, delay(attempt++));
  };

  const connect = () => {
    if (stopped) return;
    const controller = new AbortController();
    abort = controller;
    const url = `${opts.config.baseUrl}${opts.path}`;
    const source = transformHttpEventStream(
      runHttpRequest(async () => {
        const res = await fetchFn(url, {
          method: "GET",
          headers: { Authorization: `Bearer ${opts.config.token}`, Accept: "text/event-stream" },
          signal: controller.signal,
        });
        if (isAuthFailure(res.status)) {
          stopped = true;
          opts.onAuthError?.();
          throw new Error("unauthorized");
        }
        return res;
      }),
    );
    const sub = source.subscribe({
      next: (event) => {
        attempt = 0;
        if (opts.onEvent(event as unknown as FeedEvent)) opts.onStatus("live");
        else retry();
      },
      error: retry,
      complete: retry,
    });
    unsubscribe = () => sub.unsubscribe();
  };

  connect();
  return () => {
    stopped = true;
    if (timer) clearTimeout(timer);
    unsubscribe?.();
    abort?.abort();
  };
}

export type AnswerResult =
  | { ok: true; seq: number }
  | { ok: false; error: string; detail: string; auth?: boolean };

/** A consent answer goes to the host as plain JSON; the host asks the owner key to sign it. */
export async function postAnswer(
  config: HostConfig,
  body: { interrupt_id: string; consent: boolean; choice?: string },
  fetchFn: Fetch = (url, init) => fetch(url, init),
): Promise<AnswerResult> {
  assertAllowedBase(config.baseUrl);
  const res = await fetchFn(`${config.baseUrl}/v1/agent/answers`, {
    method: "POST",
    headers: { Authorization: `Bearer ${config.token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (res.ok) return { ok: true, seq: Number(json.seq ?? 0) };
  // The host also answers 403 with an error code for a request that is not yours: that is a
  // refused answer, not a refused token.
  if (res.status === 401 || (res.status === 403 && !json.error)) {
    return { ok: false, error: "unauthorized", detail: "", auth: true };
  }
  return { ok: false, error: String(json.error ?? res.status), detail: String(json.detail ?? "") };
}
