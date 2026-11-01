// SPDX-License-Identifier: Apache-2.0
import { Glasses, type GlassesProps } from "./Glasses";
import "./glasses.css";

/** The glasses card filling the viewport, centred, for a future `/glasses` route. */
export function GlassesPage(props: GlassesProps) {
  return (
    <main className="ck-gl-page">
      <Glasses {...props} />
    </main>
  );
}
