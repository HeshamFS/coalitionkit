// SPDX-License-Identifier: Apache-2.0
import { Action, Checks, type Props, type Send } from "../f08/shared";
import "../../styles/f09.css";

export function VerifyPanel({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <Checks items={p.checks} />
      <div className="row">
        <Action
          label="Run verification"
          event="verify.run"
          send={send}
          data={{ export: p.export }}
          primary
        />
        <Action label="Download log" event="log.download" send={send} data={{ export: p.export }} />
      </div>
    </>
  );
}
