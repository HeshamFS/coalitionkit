// SPDX-License-Identifier: Apache-2.0
import { Action, Fields, list, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function EvidenceCard({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="f09-media">
        <span>{list(p.masks).length ? "Masked evidence" : text(p.kind)}</span>
      </div>
      <Fields values={{ Task: p.task, Captured: p.captured_at, "Verified by": p.verified_by }} />
      <Action label="Open evidence" event="evidence.open" send={send} data={{ ref: p.ref }} />
    </>
  );
}
