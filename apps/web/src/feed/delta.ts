// SPDX-License-Identifier: Apache-2.0
import { applyPatch, type Operation } from "fast-json-patch";

export type ViewerState = Record<string, unknown>;

export class DeltaError extends Error {}

/** Apply an RFC 6902 patch to a copy of the state. Throws DeltaError when it does not fit. */
export function applyDelta(state: ViewerState | null, ops: Operation[]): ViewerState {
  if (state === null) throw new DeltaError("a delta arrived before any snapshot");
  try {
    const copy = structuredClone(state);
    // The host sends a root replacement ("path": ""), so the result is read from the return value.
    const result = applyPatch(copy, ops, true, false);
    return (result.newDocument ?? copy) as ViewerState;
  } catch (cause) {
    throw new DeltaError(cause instanceof Error ? cause.message : "bad patch");
  }
}
