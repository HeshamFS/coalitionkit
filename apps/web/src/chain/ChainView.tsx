// SPDX-License-Identifier: Apache-2.0
import { Fragment, useEffect, useRef, useState } from "react";
import "./chain.css";
import { type ChainRow, chainRows, shortHash } from "./input";
import { checkPin } from "./pin";
import { type CheckName, type VerifyInput, type VerifyResult, verifyLog } from "./verify";

export { chainInputFrom } from "./input";

const CHECK_LABEL: Record<CheckName, string> = {
  signature: "host signature",
  gap: "sequence gap",
  genesis: "genesis link",
  link: "hash link",
  receipt: "receipt",
};

const NOTES = [
  {
    title: "Replay any moment",
    body: "Scrub the timeline and every screen rebuilds exactly as it was, for the person who saw it.",
  },
  {
    title: "Who decided what",
    body: "Each yes is signed by its owner's key, not their agent's. An agent cannot say yes for you.",
  },
  {
    title: "Private stays private",
    body: "You verify the chain with hashes. You never see an event outside your scope.",
  },
];

type Run = { state: "idle" } | { state: "running" } | { state: "done"; result: VerifyResult };

export type ChainViewProps = {
  /** What the feed holds, or `null` while the log is not in the feed. */
  input: VerifyInput | null;
  /** Display rows; drawn from `input.entries` when omitted. */
  rows?: ChainRow[];
};

function summary(run: Run): string {
  if (run.state !== "done") return "";
  const r = run.result;
  if (!r.ok) {
    return `Broken at seq ${r.seq} · ${CHECK_LABEL[r.check]} check failed: ${r.detail}`;
  }
  if (r.coveredByReceipt === null) {
    return `Verified up to seq ${r.verifiedTo} · no receipt kept, so a cut or edited tail would not show`;
  }
  const rest =
    r.coveredByReceipt < r.verifiedTo
      ? ` · entries after seq ${r.coveredByReceipt} have no receipt`
      : "";
  return `Verified up to seq ${r.verifiedTo} · covered by your receipt at seq ${r.coveredByReceipt}${rest}`;
}

function pill(row: ChainRow, run: Run): string | null {
  if (run.state !== "done" || !run.result.ok || row.seq > run.result.verifiedTo) return null;
  return row.kind === "projection" ? "host-signed" : "linked";
}

function Link({ row, run }: { row: ChainRow; run: Run }) {
  const failed = run.state === "done" && !run.result.ok && run.result.seq === row.seq;
  const verified = pill(row, run);
  const cls = ["ck-chain-card", row.kind === "stub" ? "is-stub" : "", failed ? "is-broken" : ""];
  return (
    <li
      className={cls.filter(Boolean).join(" ")}
      style={{ animationDelay: `${(row.seq % 8) * 0.08}s` }}
    >
      <span className="ck-chain-seq">seq {row.seq}</span>
      <span className="ck-chain-type">{row.type}</span>
      <span className="ck-chain-hash">{failed ? "link broken" : shortHash(row.hash)}</span>
      {verified ? <span className="ck-chain-pill">{verified}</span> : null}
    </li>
  );
}

function Connector({ rows, index, run }: { rows: ChainRow[]; index: number; run: Run }) {
  const next = rows[index + 1];
  const bad = run.state === "done" && !run.result.ok && next?.seq === run.result.seq;
  const good = run.state === "done" && run.result.ok;
  return (
    <li
      className={`ck-chain-join${bad ? " is-broken" : good ? " is-ok" : ""}`}
      aria-hidden="true"
    />
  );
}

/** A broken receipt can name a seq the log never reached: draw the missing link. */
function Missing({ rows, run }: { rows: ChainRow[]; run: Run }) {
  if (run.state !== "done" || run.result.ok) return null;
  const at = run.result.seq;
  if (at <= (rows[rows.length - 1]?.seq ?? 0)) return null;
  return (
    <>
      <li className="ck-chain-join is-broken" aria-hidden="true" />
      <li className="ck-chain-card is-broken">
        <span className="ck-chain-seq">seq {at}</span>
        <span className="ck-chain-type">missing</span>
        <span className="ck-chain-hash">not in the log</span>
      </li>
    </>
  );
}

function Chain({ rows, run }: { rows: ChainRow[]; run: Run }) {
  const covered = run.state === "done" && run.result.ok ? run.result.coveredByReceipt : null;
  return (
    <ol className="ck-chain-row" aria-label="Log entries in order">
      {rows.map((row, index) => (
        <Fragment key={`${row.seq}-${row.hash}`}>
          <Link row={row} run={run} />
          {index < rows.length - 1 ? <Connector rows={rows} index={index} run={run} /> : null}
        </Fragment>
      ))}
      <Missing rows={rows} run={run} />
      {covered !== null ? (
        <li className="ck-chain-receipt">receipt · head matches · seq {covered}</li>
      ) : null}
    </ol>
  );
}

function useRows(input: VerifyInput | null, given: ChainRow[] | undefined): ChainRow[] {
  const [rows, setRows] = useState<ChainRow[]>([]);
  useEffect(() => {
    if (given || !input) return;
    let live = true;
    chainRows(input.entries).then(
      (next) => live && setRows(next),
      () => live && setRows([]),
    );
    return () => {
      live = false;
    };
  }, [input, given]);
  return given ?? rows;
}

export function ChainView({ input, rows: given }: ChainViewProps) {
  const [run, setRun] = useState<Run>({ state: "idle" });
  // The input a result belongs to: a result for an earlier log is never shown against a newer one.
  const current = useRef(input);
  current.current = input;
  const [pinned, setPinned] = useState(true);
  const rows = useRows(input, given);
  // A new log is a new question: forget the last answer.
  // biome-ignore lint/correctness/useExhaustiveDependencies: reset only when the input changes
  useEffect(() => setRun({ state: "idle" }), [input]);

  const verify = async () => {
    if (!input) return;
    const asked = input;
    setRun({ state: "running" });
    const pin = checkPin(asked.coalitionId, asked.hostKey as { x?: unknown });
    if (!pin.ok) {
      setRun({
        state: "done",
        result: { ok: false, seq: 0, check: "signature", detail: pin.detail },
      });
      return;
    }
    setPinned(pin.pinned);
    const result = await verifyLog(asked).catch(
      (error): VerifyResult => ({
        ok: false,
        seq: 0,
        check: "signature",
        detail: error instanceof Error ? error.message : "the check could not run",
      }),
    );
    if (current.current !== asked) return;
    setRun({ state: "done", result });
  };

  const heading =
    run.state === "done"
      ? run.result.ok
        ? "Verified"
        : "Not verified"
      : "Your record, not yet verified";
  const text = summary(run);
  const bad = run.state === "done" && !run.result.ok;

  return (
    <section className="ck-chain" aria-labelledby="ck-chain-title">
      <header className="ck-chain-head">
        <p className="ck-chain-eyebrow">Signed, hash-chained, replayable</p>
        <h2 id="ck-chain-title" className="ck-chain-title">
          Every decision is a link. <em>Change one, the chain breaks.</em>
        </h2>
      </header>

      {run.state === "done" && run.result.ok && !pinned && (
        <p className="ck-chain-note" role="note">
          Checked against the key this log carries. This browser did not see the host key when you
          joined, so a host that swapped its key would not show here.
        </p>
      )}
      {input === null ? (
        <p className="ck-chain-empty" role="status">
          The log is not in your feed yet
        </p>
      ) : (
        <div className="ck-chain-block">
          <div className="ck-chain-bar">
            <span className="ck-chain-label">{heading}</span>
            <button
              type="button"
              className="ck-chain-verify"
              onClick={verify}
              disabled={run.state === "running" || input.entries.length === 0}
            >
              {run.state === "running"
                ? "Verifying…"
                : run.state === "done"
                  ? "Verify again"
                  : "Verify"}
            </button>
          </div>
          <div className="ck-chain-scroll">
            {rows.length > 0 ? (
              <Chain rows={rows} run={run} />
            ) : (
              <p className="ck-chain-none">{input.entries.length === 0 ? "No entries yet" : "…"}</p>
            )}
          </div>
          <p
            className={`ck-chain-result${bad ? " is-broken" : ""}`}
            role="status"
            aria-live="polite"
          >
            {text}
          </p>
        </div>
      )}

      <div className="ck-chain-notes">
        {NOTES.map((note) => (
          <div className="ck-chain-note" key={note.title}>
            <span className="ck-chain-note-title">{note.title}</span>
            <span className="ck-chain-note-body">{note.body}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
