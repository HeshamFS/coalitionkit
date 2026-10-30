// SPDX-License-Identifier: Apache-2.0
import { Bar, num, type Props, type Send, Table, text } from "../f08/shared";
import "../../styles/f11.css";

export function CostMeter({ p }: { p: Props; send: Send }) {
  {
    const ratio = num(p.total) / Math.max(0.001, num(p.budget));
    return (
      <>
        <Table data={p.rows} columns={["role", "model", "tokens", "cost"]} />
        <div className="row">
          <b>Total {text(p.total)}</b>
          <span className="h-right small">Budget {text(p.budget)}</span>
        </div>
        <Bar value={ratio} />
        <span className={ratio >= 1 ? "family-bad" : "small"}>
          {ratio >= 1
            ? "Stopped · budget reached"
            : ratio >= 0.8
              ? "Warning · 80% of budget"
              : "Within budget"}
        </span>
      </>
    );
  }
}
