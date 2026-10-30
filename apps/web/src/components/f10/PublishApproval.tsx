// SPDX-License-Identifier: Apache-2.0
import {
  Action,
  list,
  num,
  obj,
  type Props,
  type Send,
  text,
  usePreviewState,
} from "../f08/shared";
import "../../styles/f10.css";

export function PublishApproval({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  if (preview === "published")
    return <span className="badge b-signed">Published · owner signed</span>;
  {
    const spec = obj(p.spec);
    const tests = obj(p.tests);
    const ready =
      tests.state === "passed" || (num(tests.total) > 0 && num(tests.passed) === num(tests.total));
    return (
      <>
        <b className="f10-publish-title">
          Put {spec.name ? `"${text(spec.name)}"` : "this agent"} online?
        </b>
        <div className="f10-capabilities">
          {["reads", "acts", "never"].map((kind) => (
            <div className="row small" key={kind}>
              <span
                className={`badge ${kind === "reads" ? "b-estimate" : kind === "never" ? "b-vault" : "f10-acts"}`}
              >
                {kind}
              </span>
              <span>{text(spec[kind])}</span>
            </div>
          ))}
        </div>
        <div className="row small">
          <span>Joins:</span>
          {list(p.coalitions).map((c) => (
            <span className="chip" key={text(c)}>
              {text(c)}
            </span>
          ))}
        </div>
        <Action
          label="Approve and sign"
          event="publish"
          send={send}
          data={{ spec: p.spec, coalitions: p.coalitions, tests: p.tests }}
          disabled={!ready}
          primary
        />
        {!ready && <Action label="Decline" event="decline" send={send} />}
        <span className="st">
          {ready
            ? `${text(tests.passed)} / ${text(tests.total)} attack tests passed · you can take it offline any time`
            : "Locked until all attack tests pass"}
        </span>
      </>
    );
  }
}
