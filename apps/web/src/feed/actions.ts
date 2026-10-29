// SPDX-License-Identifier: Apache-2.0
// Consent is the one thing a composed tree must never be able to do. A tree can only ask the
// shell to look at an open request (focusRequest); an answer is built from the host OpenRequest
// by trusted UI (answerFor) and never from a tree action.
import type { OpenRequest } from "./agent";

type Named = { name: string; context?: Record<string, unknown> };
export type Answer = { interrupt_id: string; consent: boolean; choice?: string };

const FOCUS_EVENTS = new Set(["decide", "plan.decide", "tension.choose", "open"]);

type Subject = { kind: string; id: string; revision?: number };

const revisionOf = (v: unknown): number | undefined => {
  if (typeof v === "number") return v;
  if (v && typeof v === "object" && typeof (v as { value?: unknown }).value === "number") {
    return (v as { value: number }).value;
  }
  return undefined;
};

const asSubject = (v: unknown): Subject | null => {
  if (!v || typeof v !== "object") return null;
  const s = v as { kind?: unknown; id?: unknown; revision?: unknown };
  if (typeof s.kind !== "string" || typeof s.id !== "string") return null;
  return { kind: s.kind, id: s.id, revision: revisionOf(s.revision) };
};

/** The open request that matches kind, id and, when given, revision. Otherwise null. */
export function matchRequest(open: OpenRequest[], subject: Subject): OpenRequest | null {
  const hit = open.find((r) => r.kind === subject.kind && r.subjectId === subject.id);
  if (!hit) return null;
  if (subject.revision !== undefined && subject.revision !== hit.revision) return null;
  return hit;
}

/**
 * What a tree event may do: name an open request for the shell to focus. It never answers.
 * A stale revision or an unlisted request gives null.
 */
export function focusRequest(action: Named, open: OpenRequest[]): OpenRequest | null {
  if (!FOCUS_EVENTS.has(action.name)) return null;
  const subject = asSubject(action.context?.subject);
  return subject ? matchRequest(open, subject) : null;
}

/** The interrupt id the host builds: kind:subject:revision:decider. */
export function interruptRevision(id: string): number | null {
  const n = Number(id.split(":", 4)[2]);
  return Number.isInteger(n) ? n : null;
}

/**
 * The answer to post for a request the host listed. Refuses when the request revision and the
 * revision encoded in its interrupt id disagree, or a tension answer names no option.
 */
export function answerFor(request: OpenRequest, consent: boolean, choice?: string): Answer {
  if (interruptRevision(request.id) !== request.revision) {
    throw new Error("the request revision does not match its interrupt id");
  }
  if (request.kind === "tension_option") {
    if (!choice) throw new Error("a tension answer must name an option");
    return { interrupt_id: request.id, consent, choice };
  }
  return { interrupt_id: request.id, consent };
}
