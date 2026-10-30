// SPDX-License-Identifier: Apache-2.0
import { Bar, num, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

const money = (value: unknown) =>
  `€${num(value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}`;
export function CostMeter({ p }: { p: Props; send: Send }) {
  const total = Math.round(num(p.total) * 100);
  const budget = Math.max(1, Math.round(num(p.budget) * 100));
  const ratio = total / budget;
  return (
    <>
      <div className="row">
        <span className="answer f11-cost-total">{money(p.total)}</span>
        <span className="small">of {money(p.budget)} budget</span>
      </div>
      <Bar value={Math.round(ratio * 100) / 100} />
      <table className="tbl">
        <thead>
          <tr>
            <th>Role</th>
            <th>Model</th>
            <th className="f11-right">Cost</th>
          </tr>
        </thead>
        <tbody>
          {rows(p.rows).map((row, i) => (
            <tr key={text(row.role) || `${i}`}>
              <td>{text(row.role)}</td>
              <td>{text(row.model)}</td>
              <td className="num f11-right">{money(row.cost)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <span className={ratio >= 1 ? "st family-bad" : "st"}>
        {ratio >= 1
          ? "Stopped · budget reached"
          : total * 5 >= budget * 4
            ? "Warning · 80% of budget"
            : "warns at 80 %, stops at 100 %; matches provider usage to the cent"}
      </span>
    </>
  );
}
