// SPDX-License-Identifier: Apache-2.0
import type { ActionPayload } from "@a2ui/web_core/v0_9";
import type { Operation } from "fast-json-patch";
import { applyDelta, DeltaError, type ViewerState } from "./delta";
import { SurfaceBook, type SurfaceEntry } from "./surfaces";

/** The few fields of an AG-UI event the renderer reads. Everything else is ignored. */
export type FeedEvent = {
  type: string;
  [key: string]: unknown;
};

export type Status = "connecting" | "live" | "reconnecting";

export type FeedSnapshot = {
  status: Status;
  state: ViewerState | null;
  surfaces: SurfaceEntry[];
  steps: string[];
  runId: string | null;
  /** Set when the stream broke the rules (a delta that does not fit): the client reconnects. */
  problem: string | null;
};

const ACTIVITY_A2UI = "a2ui-surface";

export class FeedStore {
  private snap: FeedSnapshot = {
    status: "connecting",
    state: null,
    surfaces: [],
    steps: [],
    runId: null,
    problem: null,
  };
  private listeners = new Set<() => void>();
  readonly book: SurfaceBook;

  constructor(onAction: (a: ActionPayload) => void = () => {}) {
    this.book = new SurfaceBook(onAction);
    this.book.subscribe(() => this.set({ surfaces: this.book.list() }));
  }

  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };

  getSnapshot = () => this.snap;

  private set(patch: Partial<FeedSnapshot>) {
    this.snap = { ...this.snap, ...patch };
    for (const fn of this.listeners) fn();
  }

  setStatus(status: Status) {
    if (this.snap.status !== status) this.set({ status });
  }

  /** Feed one event. Returns false when the stream must be dropped and reopened. */
  handle(event: FeedEvent): boolean {
    switch (event.type) {
      case "RUN_STARTED":
        this.book.reset();
        this.set({ runId: String(event.runId ?? ""), status: "live", steps: [], problem: null });
        return true;
      case "STATE_SNAPSHOT":
        this.set({ state: structuredClone((event.snapshot ?? {}) as ViewerState), status: "live" });
        return true;
      case "STATE_DELTA":
        try {
          this.set({ state: applyDelta(this.snap.state, (event.delta ?? []) as Operation[]) });
          return true;
        } catch (error) {
          this.set({ problem: error instanceof DeltaError ? error.message : "bad delta" });
          return false;
        }
      case "ACTIVITY_SNAPSHOT": {
        if (event.activityType !== ACTIVITY_A2UI) return true;
        const content = (event.content ?? {}) as { messages?: unknown[] };
        const messages = content.messages ?? [];
        this.book.apply(surfaceIdOf(messages, String(event.messageId ?? "")), messages);
        return true;
      }
      case "STEP_STARTED":
        this.set({ steps: [...this.snap.steps, String(event.stepName ?? "")] });
        return true;
      case "STEP_FINISHED":
        this.set({ steps: this.snap.steps.filter((s) => s !== event.stepName) });
        return true;
      case "RUN_ERROR":
        this.set({ status: "reconnecting", problem: String(event.message ?? "the run failed") });
        return false;
      default:
        return true;
    }
  }

  dispose() {
    this.book.dispose();
    this.listeners.clear();
  }
}

function surfaceIdOf(messages: unknown[], messageId: string): string {
  for (const m of messages as Record<string, { surfaceId?: string } | undefined>[]) {
    for (const key of ["createSurface", "updateComponents", "updateDataModel"]) {
      const id = m[key]?.surfaceId;
      if (id) return id;
    }
  }
  return messageId.replace(/^a2ui:/, "");
}
