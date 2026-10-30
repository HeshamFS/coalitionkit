// SPDX-License-Identifier: Apache-2.0
import { Checks, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function GardenerThinking({ p }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <span className="live-dot pulse" />
        <b>{text(p.actor)} is planning</b>
      </div>
      <Checks items={p.steps} />
    </>
  );
}
