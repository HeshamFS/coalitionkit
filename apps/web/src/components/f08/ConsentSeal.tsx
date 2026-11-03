// SPDX-License-Identifier: Apache-2.0
import { useEffect, useRef, useState } from "react";
import "../../styles/trusted-seal.css";

/** A receipt supplied only by the trusted host answer callback, never catalog data. */
export type ConsentAcknowledgement = { seq: number; signature: string };
export const CONSENT_HOLD_MS = 1200;

export function TrustedConsentSeal({
  onApprove,
  deadline,
}: {
  onApprove: (() => void) | (() => Promise<ConsentAcknowledgement | undefined>);
  deadline?: string;
}) {
  const [holding, setHolding] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [pending, setPending] = useState(false);
  const [receipt, setReceipt] = useState<ConsentAcknowledgement>();
  const [error, setError] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const sent = useRef(false);
  const mounted = useRef(true);
  const expired = () => !!deadline && Date.parse(deadline) <= Date.now();
  const cancel = () => {
    clearTimeout(timer.current);
    timer.current = undefined;
    setHolding(false);
  };
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      clearTimeout(timer.current);
    };
  }, []);
  const approve = async () => {
    cancel();
    if (sent.current || expired()) return;
    sent.current = true;
    setConfirm(false);
    setPending(true);
    setError("");
    try {
      const ack = await onApprove();
      if (mounted.current && ack && Number.isSafeInteger(ack.seq) && ack.seq > 0 && ack.signature) {
        setReceipt(ack);
        setPending(false);
      }
    } catch (cause) {
      if (!mounted.current) return;
      setPending(false);
      setError(cause instanceof Error ? cause.message : "Could not send your answer.");
      // A failed response may follow a successful post. Do not submit twice.
    }
  };
  const start = () => {
    if (sent.current || timer.current || expired()) return;
    setHolding(true);
    timer.current = setTimeout(() => void approve(), CONSENT_HOLD_MS);
  };
  return (
    <div className="trusted-seal" data-state={receipt ? "signed" : holding ? "holding" : "idle"}>
      <button
        type="button"
        className="trusted-seal-control"
        aria-label="Press and hold to approve"
        disabled={pending || !!receipt || sent.current || expired()}
        onPointerDown={(event) => {
          if (event.button === 0) start();
        }}
        onPointerUp={cancel}
        onPointerLeave={cancel}
        onPointerCancel={cancel}
        onBlur={cancel}
        onClick={(event) => {
          if (event.detail === 0 && !sent.current) setConfirm(true);
        }}
      >
        <svg viewBox="0 0 120 120" aria-hidden="true">
          <circle className="seal-track" cx="60" cy="60" r="48" />
          <circle className="seal-progress" cx="60" cy="60" r="48" transform="rotate(-90 60 60)" />
          <circle className="seal-core" cx="60" cy="60" r="38" />
          {receipt && <path d="M44 61 L55 72 L77 49" />}
        </svg>
        {!receipt && <span>Hold</span>}
      </button>
      <span className="small">Press and hold to say yes. The host signs it for you.</span>
      <button
        type="button"
        className="btn btn-ghost"
        disabled={pending || sent.current || expired()}
        onClick={() => setConfirm(true)}
      >
        Review and approve
      </button>
      {confirm && (
        <fieldset aria-label="Confirm consent">
          <p>Say yes to this revision? The host signs it for you after your yes.</p>
          <button type="button" className="btn btn-primary" onClick={() => void approve()}>
            Confirm approval
          </button>
          <button type="button" className="btn" onClick={() => setConfirm(false)}>
            Cancel
          </button>
        </fieldset>
      )}
      <SealStatus receipt={receipt} pending={pending} holding={holding} />
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

function SealStatus({
  receipt,
  pending,
  holding,
}: {
  receipt?: ConsentAcknowledgement;
  pending: boolean;
  holding: boolean;
}) {
  return (
    <div role="status" className="seal-status">
      {receipt ? (
        <>
          <b>Signed.</b>
          <span>
            consent · seq {receipt.seq} · sig {receipt.signature.slice(0, 4)}…
            {receipt.signature.slice(-2)}
          </span>
        </>
      ) : pending ? (
        "Answer sent. Waiting for the host’s acknowledgement."
      ) : holding ? (
        "Keep holding · release to cancel"
      ) : (
        ""
      )}
    </div>
  );
}
