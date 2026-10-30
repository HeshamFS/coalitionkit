// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

import { Metric } from "./controls";
export function Scorecard({ p }: { p: Props; send: Send }) {
  return (
    <div className="f11-scorecard">
      {rows(p.tiles).map((tile, i) => (
        <Metric key={text(tile.label) || `${i}`} p={tile} />
      ))}
    </div>
  );
}
