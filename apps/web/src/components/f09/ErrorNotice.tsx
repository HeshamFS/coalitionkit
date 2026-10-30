// SPDX-License-Identifier: Apache-2.0
import { Action, obj, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function ErrorNotice({ p, send }: { p: Props; send: Send }) {
  return (
    <div className="banner bn-warn" role="alert">
      <div className="grow">
        <b>{text(p.code).replaceAll("_", " ")}</b>
        <p className="small">{text(obj(p.detail).message ?? obj(p.detail).reason)}</p>
      </div>
      {obj(p.detail).retry !== false && (
        <Action label="Retry" event="error.retry" send={send} data={{ ref: p.ref, code: p.code }} />
      )}
    </div>
  );
}
