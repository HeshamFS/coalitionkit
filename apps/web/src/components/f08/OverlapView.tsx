// SPDX-License-Identifier: Apache-2.0
import { list, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function OverlapView({ p }: { p: Props; send: Send }) {
  return (
    <>
      <div className="f08-overlap">
        <div>
          <span className="eyebrow">Parties</span>
          {list(p.parties).map((v) => (
            <div className="card" key={text(v)}>
              {text(v)}
            </div>
          ))}
        </div>
        <div>
          <span className="eyebrow">Blinded, on the wire</span>
          {list(p.tokens).map((v) => (
            <div className="card card-2 mono" key={text(v)}>
              {text(v)}
            </div>
          ))}
        </div>
        <div className="card card-live">
          <span className="eyebrow">What anyone learns</span>
          <b>{text(p.result)}</b>
          <span>{text(p.mode)}</span>
        </div>
      </div>
      <span className="st">Nonmatching inputs stay private.</span>
    </>
  );
}
