// SPDX-License-Identifier: Apache-2.0
// The phone-input routes. The clip or photo is sent as the raw request body with the viewer token,
// to the same allowed origin as every other room route; the host reads it and keeps only words.
import { assertAllowedBase, type HostConfig, readConfig } from "../../feed/config";
import type { Fetch } from "../../feed/connection";
import type { Call, SayReply } from "../api";

/** What the host read: the words, and for a question the proposed answer in its closed kind. */
export type Reading = {
  text: string;
  ms: number;
  answer: unknown;
  words: string;
  description: string;
};

export type InputsIo = {
  voice: (wav: Blob, questionId?: string) => Promise<Call<Reading>>;
  photo: (image: Blob, questionId?: string) => Promise<Call<Reading>>;
  /** A confirmed sentence, marked with how it was made. */
  say: (text: string, via: "voice" | "photo") => Promise<Call<SayReply>>;
};

const str = (v: unknown) => (typeof v === "string" ? v : "");

function reading(d: Record<string, unknown>): Reading {
  const words = str(d.words);
  return {
    text: str(d.text) || words,
    ms: typeof d.ms === "number" ? d.ms : 0,
    answer: d.answer ?? null,
    words,
    description: str(d.description),
  };
}

async function send(
  config: HostConfig | null,
  path: string,
  body: Blob | string,
  type: string,
  fetchFn: Fetch,
): Promise<Call<Record<string, unknown>>> {
  if (!config) return { ok: false, status: 401, error: "no_session", detail: "", auth: true };
  assertAllowedBase(config.baseUrl);
  let res: Response;
  try {
    res = await fetchFn(`${config.baseUrl}${path}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${config.token}`, "Content-Type": type },
      body,
    });
  } catch {
    return { ok: false, status: 0, error: "unreachable", detail: "", auth: false };
  }
  const json = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (res.ok) return { ok: true, data: json };
  return {
    ok: false,
    status: res.status,
    error: str(json.error) || String(res.status),
    detail: str(json.detail),
    auth: res.status === 401,
  };
}

const query = (q: Record<string, string | undefined>) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) if (v) p.set(k, v);
  const s = p.toString();
  return s ? `?${s}` : "";
};

export function inputsIo(
  fetchFn: Fetch = (url, init) => fetch(url, init),
  config: () => HostConfig | null = () => readConfig(),
): InputsIo {
  return {
    voice: async (wav, questionId) => {
      const r = await send(
        config(),
        `/v1/room/voice${query({ question_id: questionId })}`,
        wav,
        "audio/wav",
        fetchFn,
      );
      return r.ok ? { ok: true, data: reading(r.data) } : r;
    },
    photo: async (image, questionId) => {
      const q = questionId ? { question_id: questionId } : { purpose: "say" };
      const r = await send(
        config(),
        `/v1/room/photo${query(q)}`,
        image,
        image.type || "image/jpeg",
        fetchFn,
      );
      return r.ok ? { ok: true, data: reading(r.data) } : r;
    },
    say: async (text, via) => {
      const r = await send(
        config(),
        "/v1/room/say",
        JSON.stringify({ text, via }),
        "application/json",
        fetchFn,
      );
      if (!r.ok) return r;
      const route = r.data.route;
      return {
        ok: true,
        data: {
          route: route === "private" || route === "room" || route === "change" ? route : "other",
          reply: str(r.data.reply),
          event_id: str(r.data.event_id) || undefined,
          stopped: r.data.stopped === true,
        },
      };
    },
  };
}
