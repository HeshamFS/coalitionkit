// SPDX-License-Identifier: Apache-2.0
import { Action, Checks, type Props, rows, type Send } from "../f08/shared";
import "../../styles/f10.css";

export function AttackTests({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <Checks items={p.tests} />
      <span className="small">
        {rows(p.tests).filter((t) => t.state === "passed").length} / {rows(p.tests).length} pass
      </span>
      <Action label="Fix and re-run" event="tests.rerun" send={send} />
    </>
  );
}
