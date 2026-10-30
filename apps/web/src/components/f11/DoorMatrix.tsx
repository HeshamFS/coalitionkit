// SPDX-License-Identifier: Apache-2.0
import { Badge, list, type Props, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

export function DoorMatrix({ p }: { p: Props; send: Send }) {
  return (
    <>
      <b>{text(p.target)}</b>
      <div className="f11-doors">
        {list(p.doors).map((d) => (
          <div className="card" key={text(d)}>
            <span className="eyebrow">{text(d)}</span>
            <Badge tone="signed">supported</Badge>
          </div>
        ))}
      </div>
    </>
  );
}
