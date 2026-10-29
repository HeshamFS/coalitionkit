// SPDX-License-Identifier: Apache-2.0
import type { FeedEvent } from "./store";

export type OpenRequest = {
  id: string;
  kind: string;
  subjectId: string;
  revision: number;
  message: string;
  expiresAt?: string;
};
export type AgentLine = { id: string; text: string };

export type AgentSnapshot = {
  lines: AgentLine[];
  requests: OpenRequest[];
  /** The last answer the host refused, in the host words. */
  refusal: string | null;
  /** The request the shell is showing in trusted UI, if any. */
  focus: string | null;
};

/** Interrupts and text from the agent stream. Each run lists the requests still open. */
export class AgentStore {
  private snap: AgentSnapshot = { lines: [], requests: [], refusal: null, focus: null };
  private listeners = new Set<() => void>();
  private open = new Map<string, AgentLine>();

  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };
  getSnapshot = () => this.snap;
  private set(patch: Partial<AgentSnapshot>) {
    this.snap = { ...this.snap, ...patch };
    for (const fn of this.listeners) fn();
  }

  setFocus(id: string | null) {
    this.set({ focus: id });
  }

  setRefusal(text: string | null) {
    this.set({ refusal: text });
  }

  handle(event: FeedEvent): boolean {
    switch (event.type) {
      case "TEXT_MESSAGE_START": {
        const id = String(event.messageId);
        this.open.set(id, { id, text: "" });
        return true;
      }
      case "TEXT_MESSAGE_CONTENT": {
        const line = this.open.get(String(event.messageId));
        if (line) line.text += String(event.delta ?? "");
        return true;
      }
      case "TEXT_MESSAGE_END": {
        const line = this.open.get(String(event.messageId));
        if (line) {
          this.open.delete(line.id);
          this.set({ lines: [...this.snap.lines, line] });
        }
        return true;
      }
      case "RUN_FINISHED": {
        const outcome = event.outcome as
          | { type?: string; interrupts?: Record<string, unknown>[] }
          | undefined;
        const list = outcome?.type === "interrupt" ? (outcome.interrupts ?? []) : [];
        const requests = list.map(toRequest);
        const focus = requests.some((r) => r.id === this.snap.focus) ? this.snap.focus : null;
        this.set({ requests, focus });
        return true;
      }
      case "RUN_ERROR":
        return false;
      default:
        return true;
    }
  }
}

export function toRequest(raw: Record<string, unknown>): OpenRequest {
  const meta = (raw.metadata ?? {}) as {
    subject?: { kind?: string; id?: string; revision?: number };
  };
  const subject = meta.subject ?? {};
  return {
    id: String(raw.id),
    kind: String(subject.kind ?? ""),
    subjectId: String(subject.id ?? ""),
    revision: Number(subject.revision ?? 0),
    message: String(raw.message ?? ""),
    expiresAt: (raw.expiresAt ?? raw.expires_at) as string | undefined,
  };
}
