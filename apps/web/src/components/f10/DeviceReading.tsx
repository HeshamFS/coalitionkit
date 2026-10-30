// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, Chart, type Props, type Send, text } from "../f08/shared";
import "../../styles/f10.css";

export function DeviceReading({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <b>{text(p.source)}</b>
        <Badge tone="measured">{text(p.unit)}</Badge>
      </div>
      <Chart series={p.series} planned={p.planned} unit={p.unit} />
      <span className="small">
        Limits: {text(p.limits)} · {text(p.annotations)}
      </span>
      <Action label="Export CSV" event="reading.export" send={send} data={{ source: p.source }} />
    </>
  );
}
