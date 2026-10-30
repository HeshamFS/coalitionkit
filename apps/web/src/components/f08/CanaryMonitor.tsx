// SPDX-License-Identifier: Apache-2.0
import { Badge, list, num, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function CanaryMonitor({ p }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <b>Canaries planted</b>
        <span className="h-right num">{text(p.canaries)} / run</span>
      </div>
      <div className="row wrap">
        {list(p.surfaces).map((v) => (
          <Badge key={text(v)} tone="measured">
            {text(v)}
          </Badge>
        ))}
      </div>
      <div className="row">
        <strong className={`answer ${num(p.found) > 0 ? "family-bad" : ""}`}>
          {text(p.found)}
        </strong>
        <span className="small">found outside their vault</span>
        <Badge>{text(p.runs)} runs</Badge>
      </div>
    </>
  );
}
