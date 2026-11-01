// SPDX-License-Identifier: Apache-2.0
// A pack may order the room's panels per role and device. The order arrives in the viewer state
// (pack.views.order); it only moves panels the room already has and never adds one.

import type { ViewerState } from "./delta";
import { eventsOf } from "./derive";

export type Device = "wide" | "compact";

const isRecord = (v: unknown): v is Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v);

/** The roles the viewer asked to join with, read from the viewer's own join message. */
export function viewerRoles(state: ViewerState | null): string[] {
  const viewer = state?.viewer;
  if (typeof viewer !== "string") return [];
  const join = eventsOf(state).findLast(
    (e) => e.type === "coalition.join" && e.on_behalf_of === viewer,
  );
  const roles = join?.payload.roles_requested;
  return Array.isArray(roles) ? roles.filter((r): r is string => typeof r === "string") : [];
}

/** Component names the pack lays out for this viewer's roles and device, in order, without repeats. */
export function packOrder(state: ViewerState | null, device: Device): string[] {
  const pack = state?.pack;
  const views = isRecord(pack) ? pack.views : undefined;
  const order = isRecord(views) ? views.order : undefined;
  if (!isRecord(order)) return [];
  const names: string[] = [];
  for (const role of viewerRoles(state)) {
    const byDevice = order[role];
    const list = isRecord(byDevice) ? byDevice[device] : undefined;
    if (Array.isArray(list)) {
      for (const n of list) if (typeof n === "string" && !names.includes(n)) names.push(n);
    }
  }
  return names;
}

/** Component names the pack itself defines, which the room does not draw but also does not log. */
function packDefined(state: ViewerState | null): Set<string> {
  const pack = state?.pack;
  const views = isRecord(pack) ? pack.views : undefined;
  const components = isRecord(views) ? views.components : undefined;
  return new Set(isRecord(components) ? Object.keys(components) : []);
}

/**
 * The default panels, with those the pack names moved to the front in the pack's order. A name the
 * room has no panel for is ignored and, in development, logged. Without a pack the defaults come
 * back unchanged.
 */
export function orderPanels(
  state: ViewerState | null,
  device: Device,
  defaults: readonly string[],
): string[] {
  const named = packOrder(state, device);
  if (named.length === 0) return [...defaults];
  const defined = packDefined(state);
  const known = named.filter((n) => defaults.includes(n));
  if (import.meta.env?.DEV) {
    for (const n of named) {
      if (!defaults.includes(n) && !defined.has(n)) console.warn(`pack view names unknown ${n}`);
    }
  }
  return [...known, ...defaults.filter((n) => !known.includes(n))];
}
