// SPDX-License-Identifier: Apache-2.0
import { Bar, Chart, num, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function StepProgress({ p }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <b>{text(p.task)}</b>
        <span className="h-right small">ETA {text(p.eta)}</span>
      </div>
      <Bar value={num(p.progress)} />
      <Chart series={p.measured} planned={p.planned} />
    </>
  );
}
