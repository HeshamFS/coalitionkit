// SPDX-License-Identifier: Apache-2.0
import type { CSSProperties } from "react";
import "./dissolve.css";

/** The payload of a `coalition.dissolve` event. */
export type DissolveEvent = {
  reason: "completed" | "deadline" | "cancelled" | "budget";
  skills_written: string[];
};

/** Counts the host returned for the cleanup steps it finished. */
export type CleanupCounts = {
  tasks_closed?: number;
  tokens_revoked?: number;
  invitations_revoked?: number;
  vaults_erased?: number;
};

/** The host's cleanup report: the counts, or the step that failed and what finished before it. */
export type CleanupReport = CleanupCounts | { failed: string; done: CleanupCounts };

export type Lesson = { title: string; summary?: string };

/** Numbers for the strip. Anything not passed shows its placeholder. */
export type Measured = {
  calendarsShared?: number;
  minutes?: number | string;
  cost?: string;
  vendors?: number;
};

export type DissolveProps = {
  event: DissolveEvent;
  /** What the host returned for the cleanup. Omitted while it is still pending. */
  cleanup?: CleanupReport;
  /** Short outcome lines that fold into the mark. */
  outcomes?: string[];
  /** Titles for the written skills, by id. A skill without one shows its id. */
  lessons?: Record<string, Lesson>;
  measured?: Measured;
  /** Called by the Retry button after a failed cleanup step. */
  onRetry?: () => void;
};

const HEADLINE: Record<DissolveEvent["reason"], string> = {
  completed: "Goal met.",
  deadline: "Deadline reached.",
  cancelled: "Coalition ended.",
  budget: "Budget reached.",
};

/** Fold vectors for the six places around the mark. */
const SLOTS = [
  { x: 0, y: 0, dx: 220, dy: 180 },
  { x: 220, y: 0, dx: 0, dy: 180 },
  { x: 440, y: 0, dx: -220, dy: 180 },
  { x: 0, y: 380, dx: 220, dy: -160 },
  { x: 220, y: 380, dx: 0, dy: -160 },
  { x: 440, y: 380, dx: -220, dy: -160 },
] as const;

const SEATS = [
  [48.3, 15.7],
  [32, 9],
  [15.7, 15.7],
  [9, 32],
  [15.7, 48.3],
  [32, 55],
  [48.3, 48.3],
] as const;

type Claim = { key: string; text: string };

const isCount = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value >= 0;

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

/** One closing claim per count the host returned, and none for a count it did not. */
export function claimsFrom(counts: CleanupCounts): Claim[] {
  const claims: Claim[] = [];
  if (isCount(counts.tasks_closed)) {
    claims.push({ key: "tasks", text: `${plural(counts.tasks_closed, "task", "tasks")} closed` });
  }
  if (isCount(counts.tokens_revoked)) {
    const text = plural(counts.tokens_revoked, "viewer link", "viewer links");
    claims.push({ key: "tokens", text: `${text} revoked` });
  }
  if (isCount(counts.invitations_revoked)) {
    const text = plural(counts.invitations_revoked, "invitation", "invitations");
    claims.push({ key: "invitations", text: `${text} revoked` });
  }
  if (isCount(counts.vaults_erased)) {
    const text = plural(counts.vaults_erased, "hosted vault", "hosted vaults");
    claims.push({ key: "vaults", text: `${text} erased` });
  }
  return claims;
}

function failedStep(report: CleanupReport | undefined): string | null {
  if (!report || !("failed" in report)) return null;
  return typeof report.failed === "string" && report.failed ? report.failed : "a cleanup step";
}

function countsOf(report: CleanupReport | undefined): CleanupCounts {
  if (!report) return {};
  return "failed" in report ? (report.done ?? {}) : report;
}

function Mark() {
  return (
    <svg
      className="ck-dis-mark"
      width="150"
      height="150"
      viewBox="0 0 64 64"
      role="img"
      aria-label="The coalition mark settling as the coalition ends"
    >
      {SEATS.map(([cx, cy]) => (
        <circle key={`${cx}-${cy}`} className="ck-dis-seat" cx={cx} cy={cy} r="4.5" />
      ))}
      <circle className="ck-dis-goal" cx="32" cy="32" r="8.5" />
    </svg>
  );
}

function Closing({ report, onRetry }: Pick<DissolveProps, "onRetry"> & { report?: CleanupReport }) {
  const counts = countsOf(report);
  const claims = claimsFrom(counts);
  const failed = failedStep(report);
  const all = claims.length === 4 && failed === null;
  return (
    <div className="ck-dis-closing" role="status" aria-live="polite">
      {claims.length > 0 ? (
        <ul className="ck-dis-claims">
          {claims.map((c) => (
            <li key={c.key}>{c.text}</li>
          ))}
        </ul>
      ) : null}
      {report === undefined ? (
        <p className="ck-dis-pending">Closing up: waiting for the host</p>
      ) : null}
      {report !== undefined && failed === null && !all ? (
        <p className="ck-dis-pending">Some steps have not reported yet</p>
      ) : null}
      {all ? <p className="ck-dis-kept">Nothing kept</p> : null}
      {failed !== null ? (
        <div className="ck-dis-failed">
          <p>Cleanup stopped at: {failed}</p>
          <button type="button" className="ck-dis-retry" onClick={onRetry} disabled={!onRetry}>
            Retry
          </button>
        </div>
      ) : null}
    </div>
  );
}

function Strip({ measured }: { measured?: Measured }) {
  const m = measured ?? {};
  const cells: [string, string][] = [
    [isCount(m.calendarsShared) ? String(m.calendarsShared) : "[MEASURED]", "calendars shared"],
    [m.minutes === undefined ? "[MEASURED]" : String(m.minutes), "minutes"],
    [m.cost === undefined ? "[COST]" : m.cost, "model spend"],
    [isCount(m.vendors) ? String(m.vendors) : "[MEASURED]", "vendors' agents"],
  ];
  return (
    <div className="ck-dis-strip ck-dis-skill" style={{ animationDelay: "0.8s" }}>
      {cells.map(([value, label]) => (
        <div className="ck-dis-stat" key={label}>
          <span className="ck-dis-value">{value}</span>
          <span className="ck-dis-label">{label}</span>
        </div>
      ))}
    </div>
  );
}

export function Dissolve({
  event,
  cleanup,
  outcomes = [],
  lessons = {},
  measured,
  onRetry,
}: DissolveProps) {
  const skills = event.skills_written;
  return (
    <section className="ck-dis" aria-labelledby="ck-dis-title">
      <header className="ck-dis-head">
        <p className="ck-dis-eyebrow">The end of a coalition</p>
        <h2 id="ck-dis-title" className="ck-dis-title">
          {HEADLINE[event.reason]} <em>The table folds away; only lessons stay.</em>
        </h2>
      </header>

      <div className="ck-dis-stage">
        {outcomes.slice(0, SLOTS.length).map((text, i) => {
          const slot = SLOTS[i] ?? SLOTS[0];
          return (
            <div
              key={`slot-${slot.x}-${slot.y}`}
              className="ck-dis-fold"
              style={
                {
                  left: slot.x,
                  top: slot.y,
                  "--dx": `${slot.dx}px`,
                  "--dy": `${slot.dy}px`,
                } as CSSProperties
              }
            >
              {text}
            </div>
          );
        })}
        <Mark />
      </div>

      <div className="ck-dis-side">
        <Closing report={cleanup} onRetry={onRetry} />
        <span className="ck-dis-heading">Lessons written as skills</span>
        {skills.length === 0 ? <p className="ck-dis-pending">No lessons were written</p> : null}
        {skills.map((id, i) => {
          const lesson = lessons[id];
          return (
            <div
              className="ck-dis-skill ck-dis-lesson"
              key={id}
              style={{ animationDelay: `${i * 0.4}s` }}
            >
              <span className="ck-dis-file">SKILL.md</span>
              <span className="ck-dis-lesson-title">{lesson?.title ?? id}</span>
              {lesson?.summary ? (
                <span className="ck-dis-lesson-body">{lesson.summary}</span>
              ) : null}
            </div>
          );
        })}
        <Strip measured={measured} />
      </div>
    </section>
  );
}
