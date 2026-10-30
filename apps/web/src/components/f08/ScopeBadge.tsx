// SPDX-License-Identifier: Apache-2.0
import { list, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function ScopeBadge({ p }: { p: Props; send: Send }) {
  return (
    <span className={`scope ${p.audience === "public" ? "f08-public" : ""}`}>
      {text(p.audience)}
      {list(p.redact).length > 0 && ` − ${text(p.redact)}`}
    </span>
  );
}
