// SPDX-License-Identifier: Apache-2.0
import type { OpenRequest } from "./agent";

type Named = { name: string; context?: Record<string, unknown> };
export type Answer = { interrupt_id: string; consent: boolean; choice?: string };

const asSubject = (v: unknown): { kind: string; id: string } | null => {
  if (!v || typeof v !== "object") return null;
  const s = v as { kind?: unknown; id?: unknown };
  return typeof s.kind === "string" && typeof s.id === "string" ? { kind: s.kind, id: s.id } : null;
};

/**
 * Turn a catalog event into the consent answer it stands for, or null when the event is not a
 * decision or no open request matches. Only requests the host listed can be answered, so a tree
 * can never invent one.
 */
export function answerFor(action: Named, open: OpenRequest[]): Answer | null {
  const ctx = action.context ?? {};
  const find = (kind: string, id: string) =>
    open.find((r) => r.kind === kind && r.subjectId === id);
  if (action.name === "decide") {
    const subject = asSubject(ctx.subject);
    const consent = ctx.consent;
    if (!subject || typeof consent !== "boolean") return null;
    const req = find(subject.kind, subject.id);
    if (!req) return null;
    return req.kind === "tension_option"
      ? {
          interrupt_id: req.id,
          consent,
          choice: typeof ctx.choice === "string" ? ctx.choice : undefined,
        }
      : { interrupt_id: req.id, consent };
  }
  if (action.name === "plan.decide") {
    const subject = asSubject(ctx.subject);
    const req = subject && find("plan", subject.id);
    return req ? { interrupt_id: req.id, consent: true } : null;
  }
  if (action.name === "tension.choose") {
    const subject = asSubject(ctx.subject);
    const req = subject && find("tension_option", subject.id);
    return req && typeof ctx.option === "string"
      ? { interrupt_id: req.id, consent: true, choice: ctx.option }
      : null;
  }
  return null;
}
