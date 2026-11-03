// SPDX-License-Identifier: Apache-2.0
// Draws a list of A2UI messages the host composed (a brief question, a result, a seen-as view)
// through the same closed catalog and the same fixed-layout fallback as the feed. A tree can
// never answer a consent: its actions here only reach the callback this screen passes, and the
// consent path never sees them.
import { A2uiSurface } from "@a2ui/react/v0_9";
import type { ActionPayload } from "@a2ui/web_core/v0_9";
import { useEffect, useMemo, useRef } from "react";
import { type Surface, SurfaceBook } from "../feed/surfaces";

type Found = { id: string; model: Surface; fallback: boolean } | null;

function surfaceIdOf(messages: unknown[]): string {
  for (const m of messages as Record<string, { surfaceId?: string } | undefined>[]) {
    for (const key of ["createSurface", "updateComponents", "updateDataModel"]) {
      const id = m?.[key]?.surfaceId;
      if (id) return id;
    }
  }
  return "surface";
}

export function useSurface(messages: unknown[], onAction?: (a: ActionPayload) => void) {
  const latest = useRef(onAction);
  latest.current = onAction;
  const book = useMemo(() => new SurfaceBook((a) => latest.current?.(a)), []);
  useEffect(() => () => book.dispose(), [book]);
  // The host re-sends state often; the surface is rebuilt only when its messages really change,
  // so what a person has typed into it is not lost.
  const key = JSON.stringify(messages);
  // biome-ignore lint/correctness/useExhaustiveDependencies: `key` stands for the messages' contents
  return useMemo<Found>(() => {
    if (messages.length === 0) return null;
    const id = surfaceIdOf(messages);
    book.reset();
    book.apply(id, messages);
    return book.list().find((s) => s.id === id) ?? null;
  }, [book, key]);
}

/** A composed surface, or the plain words when the host's tree could not be drawn. */
export function ComposedSurface({
  messages,
  onAction,
  emptyText = "Nothing was composed.",
}: {
  messages: unknown[];
  onAction?: (a: ActionPayload) => void;
  emptyText?: string;
}) {
  const found = useSurface(messages, onAction);
  if (!found) return <p className="tb-quiet">{emptyText}</p>;
  if (found.fallback) {
    return (
      <p className="tb-quiet" role="note">
        The host's layout could not be drawn here, so the standard view stands in. The data is under
        "Show the work".
      </p>
    );
  }
  return <A2uiSurface surface={found.model} />;
}

/** The value a brief question holds: the surface's `/value`, else the whole data model. */
export function briefValue(model: Surface | null): unknown {
  if (!model) return undefined;
  const dm = model.dataModel;
  try {
    if (dm.hasPath("/value")) return dm.get("/value");
    const root = dm.get("/");
    return root && typeof root === "object" && Object.keys(root).length > 0 ? root : undefined;
  } catch {
    return undefined;
  }
}
