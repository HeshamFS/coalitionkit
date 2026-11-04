// SPDX-License-Identifier: Apache-2.0
// Ending a coalition: the owner's confirm step, and the closing screen both for the
// owner (with the host's report) and for anyone whose session ended after a dissolve event.
import { useCallback, useEffect, useRef, useState } from "react";
import { clearToken } from "../feed/config";
import { dissolveCoalition, HostError } from "../genesis/api";
import { clearOwner } from "../genesis/owner";
import { type CleanupReport, Dissolve, type DissolveEvent } from "../moments/Dissolve";
import "./end.css";
import { beginEnd, clearEnded, type EndRun, readEnded } from "./ended";

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
  // A request the host refused or never received ends nothing: the room and session stay.
  const [refused, setRefused] = useState("");
  const asked = useRef(false);
  const ask = useCallback((r: EndRun) => {
    setReport(undefined);
    setRefused("");
    dissolveCoalition(r.token, r.reason).then(setReport, (error: unknown) =>
      setRefused(
        error instanceof HostError
          ? `The host refused (${error.status}). Nothing was ended.`
          : "No answer came back from the host, so it is not known whether the coalition ended. Try again to find out: asking twice is safe.",
      ),
    );
  }, []);
  useEffect(() => {
    if (!run || asked.current) return;
    asked.current = true;
    ask(run);
  }, [run, ask]);
  const base = event ?? readEnded();
  // The owner's feed closes with the dissolve; the host's report names the lessons too.
  const counts = report && "failed" in report ? report.done : report;
  const shown: DissolveEvent = {
    reason: run?.reason ?? base?.reason ?? "completed",
    skills_written: base?.skills_written?.length
      ? base.skills_written
      : (counts?.skills_written ?? base?.skills_written ?? []),
  };
  if (run && refused) {
    return (
      <main className="ck-ended" aria-label="The coalition was not ended">
        <p className="ck-ended-refused" role="alert">
          {refused}
        </p>
        <p className="ck-ended-out">
          <button type="button" className="btn" onClick={() => ask(run)}>
            Try again
          </button>
          <button type="button" className="btn btn-primary" onClick={() => beginEnd(null)}>
            Back to the room
          </button>
        </p>
      </main>
    );
  }
  return (
    <main className="ck-ended" aria-label="The coalition has ended">
      <Dissolve
        event={shown}
        cleanup={report}
        lessons={counts?.lessons}
        onRetry={run ? () => ask(run) : undefined}
      />
      <p className="ck-ended-out">
        <button type="button" className="btn" onClick={() => leave(onLeave)}>
          Back to the start
        </button>
      </p>
    </main>
  );
}
