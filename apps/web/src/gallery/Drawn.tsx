// SPDX-License-Identifier: Apache-2.0
// The sheet pages draw every example through the A2UI processor and the registered catalog, the
// same path the room uses, so a sheet only renders what the catalog's schemas accept.
import { A2uiSurface } from "@a2ui/react/v0_9";
import { useMemo } from "react";
import { SurfaceBook } from "../feed/surfaces";

let next = 0;

export type Node = { id: string; component: string } & Record<string, unknown>;

/**
 * One surface. `components` must include `root`; `data` is the data model the tree binds to.
 * A tree the catalog refuses shows the fixed fallback, which marks the example as wrong.
 */
export function Drawn({
  components,
  data = {},
  label,
}: {
  components: Node[];
  data?: Record<string, unknown>;
  label?: string;
}) {
  const surface = useMemo(() => {
    next += 1;
    const id = `sheet-${next}`;
    const book = new SurfaceBook(() => {});
    book.apply(id, [
      { version: "v0.9", createSurface: { surfaceId: id, catalogId: "coalitionkit/v0_9" } },
      { version: "v0.9", updateComponents: { surfaceId: id, components } },
      { version: "v0.9", updateDataModel: { surfaceId: id, path: "/", value: data } },
    ]);
    return book.list()[0];
  }, [components, data]);
  if (!surface) return null;
  return (
    <div className="drawn" data-fallback={surface.fallback || undefined} data-label={label}>
      <A2uiSurface surface={surface.model} />
    </div>
  );
}

/** A single component as the root of its own surface, the common case on a sheet. */
export function One({
  component,
  props,
  data,
  label,
}: {
  component: string;
  props: Record<string, unknown>;
  data?: Record<string, unknown>;
  label?: string;
}) {
  const components = useMemo(() => [{ id: "root", component, ...props }], [component, props]);
  return <Drawn components={components} data={data} label={label} />;
}
