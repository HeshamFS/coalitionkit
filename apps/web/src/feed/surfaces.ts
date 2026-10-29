// SPDX-License-Identifier: Apache-2.0

import type { ReactCatalogComponent } from "@a2ui/react/v0_9";
import { type ActionPayload, MessageProcessor, type SurfaceModel } from "@a2ui/web_core/v0_9";
import { CATALOG_ID, coalitionCatalog } from "../catalog";

export type Surface = SurfaceModel<ReactCatalogComponent>;
export type SurfaceEntry = { id: string; model: Surface; fallback: boolean };
export type FallbackField = { label: string; value: string };

const VERSION = "v0.9" as const;
const ROOT = "root";

/** The fixed layout, byte for byte what the host sends when its own validation fails. */
export function fallbackMessages(surfaceId: string, fields: FallbackField[] = []) {
  return [
    { version: VERSION, createSurface: { surfaceId, catalogId: CATALOG_ID } },
    {
      version: VERSION,
      updateComponents: {
        surfaceId,
        components: [
          { id: ROOT, component: "Card", title: "Standard view", fields: { path: "/fields" } },
        ],
      },
    },
    { version: VERSION, updateDataModel: { surfaceId, path: "/", value: { fields } } },
  ];
}

/**
 * Surfaces for one run. A tree the catalog refuses, or one without a root, is replaced by the
 * fixed layout, so a bad tree never leaves a blank screen or a half-drawn one.
 */
export class SurfaceBook {
  private processor: MessageProcessor;
  private fallbacks = new Set<string>();
  private fields: FallbackField[] = [];
  private listeners = new Set<() => void>();

  constructor(private readonly onAction: (a: ActionPayload) => void) {
    this.processor = this.makeProcessor();
  }

  private makeProcessor() {
    return new MessageProcessor([coalitionCatalog], (a) => this.onAction(a));
  }

  subscribe(fn: () => void) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private changed() {
    for (const fn of this.listeners) fn();
  }

  /** A new run replays every surface, so start from nothing. */
  reset() {
    this.processor.dispose();
    this.fallbacks.clear();
    this.processor = this.makeProcessor();
    this.changed();
  }

  setFallbackFields(fields: FallbackField[]) {
    this.fields = fields;
    for (const id of this.fallbacks) {
      this.processor.processMessages({
        version: VERSION,
        updateDataModel: { surfaceId: id, path: "/", value: { fields } },
      } as never);
    }
  }

  apply(surfaceId: string, messages: unknown[]) {
    let ok = false;
    try {
      refuseUnknown(messages);
      this.processor.processMessages(messages as never);
      ok = this.processor.getSurface(surfaceId)?.componentsModel.get(ROOT) !== undefined;
    } catch {
      ok = false;
    }
    if (ok) this.fallbacks.delete(surfaceId);
    else this.installFallback(surfaceId);
    this.changed();
  }

  private installFallback(surfaceId: string) {
    if (this.processor.getSurface(surfaceId)) this.processor.model.deleteSurface(surfaceId);
    this.processor.processMessages(fallbackMessages(surfaceId, this.fields) as never);
    this.fallbacks.add(surfaceId);
  }

  list(): SurfaceEntry[] {
    return [...this.processor.getSurfaces()].map(([id, model]) => ({
      id,
      model: model as Surface,
      fallback: this.fallbacks.has(id),
    }));
  }

  dispose() {
    this.processor.dispose();
    this.listeners.clear();
  }
}

/** The closed catalog: a component the catalog does not hold is refused, whatever else is valid. */
function refuseUnknown(messages: unknown[]) {
  for (const m of messages as { updateComponents?: { components?: { component?: unknown }[] } }[]) {
    for (const c of m.updateComponents?.components ?? []) {
      if (typeof c.component !== "string" || !coalitionCatalog.components.has(c.component)) {
        throw new Error(`component ${String(c.component)} is not in the catalog`);
      }
    }
  }
}
