// SPDX-License-Identifier: Apache-2.0
import {
  Action,
  Fields,
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
        <b>Put this agent online?</b>
        <Fields values={{ Reads: spec.reads, Acts: spec.acts, Never: spec.never }} />
        <div className="row small">Joins: {text(p.coalitions)}</div>
        <Action
          label="Approve and sign"
          event="publish"
          send={send}
          data={{ spec: p.spec, coalitions: p.coalitions, tests: p.tests }}
          disabled={!ready}
          primary
        />
        <Action label="Decline" event="decline" send={send} />
        <span className="st">
          {ready
            ? "Attack tests passed · you can take it offline any time"
            : "Locked until all attack tests pass"}
        </span>
      </>
    );
  }
}
