// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function ProjectionNote({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <Badge tone="signed">projection</Badge>
      <span>{text(p.removed)} hidden</span>
      <div className="banner bn-info">
        The host signed this version for you. It links to the original by hash, so you can prove it
        wasn't altered.
      </div>
      <Action label="Verify" event="projection.verify" send={send} data={{ source: p.source }} />
    </>
  );
}
