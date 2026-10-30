// SPDX-License-Identifier: Apache-2.0
import { type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

const labels: Record<string, string> = {
  measured: "Measured",
  vault: "Vault answer",
  signed: "Signed",
  model: "Model output",
  estimate: "Estimate",
};
export function ProvenanceTag({ p }: { p: Props; send: Send }) {
  return (
    <span className={`badge b-${text(p.kind)}`} title={text(p.source)}>
      {labels[text(p.kind)] ?? text(p.kind)}
    </span>
  );
}
