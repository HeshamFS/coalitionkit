// SPDX-License-Identifier: Apache-2.0
import { Badge, list, num, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function CanaryMonitor({ p }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <b style={{ fontSize: 13 }}>Canaries planted</b>
        <span className="h-right num">{text(p.canaries)} / run</span>
      </div>
      <div className="f08-surfaces">
        {list(p.surfaces).map((v) => (
          <span key={text(v)} className="slot slot-best">
            {text(v)}
          </span>
        ))}
      </div>
      <div className="row">
        <strong
          style={{ fontSize: 20 }}
          className={`answer ${num(p.found) > 0 ? "family-bad" : ""}`}
        >
          {text(p.found)}
        </strong>
        <span className="small">found outside their vault</span>
        <span className="h-right">
          <Badge tone="measured">{text(p.runs)} runs</Badge>
        </span>
      </div>
      <span className="st">adversarial agents scripted to extract them</span>
    </>
  );
}
