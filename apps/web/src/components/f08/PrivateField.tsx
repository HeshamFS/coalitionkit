// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function PrivateField({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <Badge tone="vault">{text(p.policy) || "vault"}</Badge>
      </div>
      <div className="input">
        <span className="grow">{text(p.display)}</span>
        <Action label="Reveal" event="field.reveal" send={send} data={{ seconds: p.reveal }} />
      </div>
      <span className="st">Hidden on screen too · show for {text(p.reveal) || "10"} s</span>
    </>
  );
}
