// SPDX-License-Identifier: Apache-2.0
// After a yes: "Signed." with the host's receipt (Consent board, final state). Shown only when the
// host acknowledged the answer with a sequence number and signature.
export function SignedNotice({
  question,
  seq,
  signature,
  onClose,
}: {
  question: string;
  seq: number;
  signature: string;
  onClose: () => void;
}) {
  const sig = signature.length > 10 ? `${signature.slice(0, 4)}…${signature.slice(-2)}` : signature;
  return (
    <section className="room-signed" role="status" aria-label="Signed">
      <svg width="28" height="28" viewBox="0 0 120 120" aria-hidden="true">
        <circle cx="60" cy="60" r="48" fill="var(--blue)" />
        <path
          d="M44 61 L55 72 L77 49"
          fill="none"
          stroke="var(--on-blue)"
          strokeWidth="9"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <div className="room-signed-text">
        <b>Signed.</b> <span>{question.replace(/\?$/, "")}: yes</span>
        <span className="room-signed-receipt">
          consent · seq {seq} · sig {sig}
        </span>
      </div>
      <button type="button" className="btn btn-sm" onClick={onClose}>
        Done
      </button>
    </section>
  );
}
