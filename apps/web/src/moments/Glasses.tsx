// SPDX-License-Identifier: Apache-2.0
import "./glasses.css";

export type GlassesProps = {
  /** The member's current step, counted from 1. */
  step: number;
  total: number;
  /** The one thing to do now. */
  instruction: string;
  /** The line beside the control glyph. */
  detail?: string;
  /** A quieter second line under the detail. */
  note?: string;
  /** The control the instruction names; shown large. */
  glyph?: string;
};

const MARK = [
  [48.3, 15.7],
  [32, 9],
  [15.7, 15.7],
  [9, 32],
  [15.7, 48.3],
  [32, 55],
  [48.3, 48.3],
] as const;

function Mark() {
  return (
    <svg className="ck-gl-mark" width="26" height="26" viewBox="0 0 64 64" aria-hidden="true">
      {MARK.map(([cx, cy]) => (
        <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="5" fill="#ffffff" />
      ))}
      <circle cx="32" cy="32" r="9" fill="#4d8dff" />
    </svg>
  );
}

function Progress({ step, total }: { step: number; total: number }) {
  const label = `Step ${step} of ${total}`;
  if (total > 24) {
    return (
      <div
        className="ck-gl-bar"
        role="progressbar"
        aria-label={label}
        aria-valuemin={1}
        aria-valuemax={total}
        aria-valuenow={step}
      >
        <span className="ck-gl-fill" style={{ width: `${(step / total) * 100}%` }} />
      </div>
    );
  }
  return (
    <div
      className="ck-gl-steps"
      role="progressbar"
      aria-label={label}
      aria-valuemin={1}
      aria-valuemax={total}
      aria-valuenow={step}
    >
      {Array.from({ length: total }, (_, i) => (
        <span
          // The segments never reorder: their position is their meaning.
          // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length list
          key={i}
          className={`ck-gl-seg${i < step - 1 ? " is-done" : i === step - 1 ? " is-now" : ""}`}
        />
      ))}
    </div>
  );
}

/** The glasses card: 600 x 600, black, one step and one instruction. */
export function Glasses({ step, total, instruction, detail, note, glyph = "▲" }: GlassesProps) {
  const count = Math.max(1, Math.floor(total));
  const at = Math.min(count, Math.max(1, Math.floor(step)));
  return (
    <section className="ck-gl" aria-label="Your step">
      <div className="ck-gl-top">
        <Mark />
        <span className="ck-gl-count">
          Your step · {at} of {count}
        </span>
      </div>
      <p className="ck-gl-instruction">{instruction}</p>
      <div className="ck-gl-row">
        <div className="ck-gl-glyph" aria-hidden="true">
          {glyph}
        </div>
        <div className="ck-gl-text">
          {detail ? <span className="ck-gl-detail">{detail}</span> : null}
          {note ? <span className="ck-gl-note">{note}</span> : null}
        </div>
      </div>
      <Progress step={at} total={count} />
      <span className="ck-gl-say">Say “done” or “skip” · agents never press buttons</span>
    </section>
  );
}
