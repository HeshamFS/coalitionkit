// SPDX-License-Identifier: Apache-2.0
// Ending a coalition (story J-13): the owner's confirm step, and the closing screen both for the
// owner (with the host's report) and for anyone whose session ended after a dissolve event.
import { useCallback, useEffect, useRef, useState } from "react";
import { clearToken } from "../feed/config";
import { dissolveCoalition } from "../genesis/api";
import { clearOwner } from "../genesis/owner";
import { type CleanupReport, Dissolve, type DissolveEvent } from "../moments/Dissolve";
import "./end.css";
import { clearEnded, type EndRun, readEnded } from "./ended";

type Reason = EndRun["reason"];

export function EndConfirm({
  onConfirm,
  onCancel,
}: {
  onConfirm: (reason: Reason) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState<Reason>("completed");
  return (
    <div className="ck-end-scrim">
      <section className="ck-end" role="dialog" aria-modal="true" aria-label="End this coalition">
        <h2 className="ck-end-q">End this coalition for everyone?</h2>
        <p className="ck-end-p">
          Open tasks close, everyone's access ends, hosted vaults are erased.
        </p>
        <fieldset className="ck-end-why">
          <legend>Why it ends</legend>
          <label>
            <input
              type="radio"
              name="end-reason"
              checked={reason === "completed"}
              onChange={() => setReason("completed")}
            />
            The goal is met
          </label>
          <label>
            <input
              type="radio"
              name="end-reason"
              checked={reason === "cancelled"}
              onChange={() => setReason("cancelled")}
            />
            Called off
          </label>
        </fieldset>
        <div className="ck-end-actions">
          <button type="button" className="btn" onClick={onCancel}>
            Keep going
          </button>
          <button type="button" className="btn btn-primary" onClick={() => onConfirm(reason)}>
            End coalition
          </button>
        </div>
      </section>
    </div>
  );
}

function leave(done: () => void) {
  clearToken();
  clearOwner();
  clearEnded();
  done();
}

/**
 * The closing screen. With a `run` it asks the host to dissolve and shows the report (Retry asks
 * again); without one it shows the event the room last received, with no cleanup counts.
 */
export function EndedView({
  run,
  event,
  onLeave,
}: {
  run?: EndRun;
  event?: DissolveEvent | null;
  onLeave: () => void;
}) {
  const [report, setReport] = useState<CleanupReport | undefined>();
  const asked = useRef(false);
  const ask = useCallback((r: EndRun) => {
    setReport(undefined);
    dissolveCoalition(r.token, r.reason).then(setReport, () =>
      setReport({ failed: "reaching the host", done: {} }),
    );
  }, []);
  useEffect(() => {
    if (!run || asked.current) return;
    asked.current = true;
    ask(run);
  }, [run, ask]);
  const base = event ?? readEnded();
  const shown: DissolveEvent = {
    reason: run?.reason ?? base?.reason ?? "completed",
    skills_written: base?.skills_written ?? [],
  };
  return (
    <main className="ck-ended" aria-label="The coalition has ended">
      <Dissolve event={shown} cleanup={report} onRetry={run ? () => ask(run) : undefined} />
      <p className="ck-ended-out">
        <button type="button" className="btn" onClick={() => leave(onLeave)}>
          Back to the start
        </button>
      </p>
    </main>
  );
}
