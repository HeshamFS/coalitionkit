// SPDX-License-Identifier: Apache-2.0
import { Badge, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function ProvenanceTag({ p }: { p: Props; send: Send }) {
  return (
    <Badge tone={text(p.kind)}>
      {text(p.kind)}
      {p.source ? ` · ${text(p.source)}` : ""}
    </Badge>
  );
}
