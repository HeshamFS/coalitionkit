// SPDX-License-Identifier: Apache-2.0
/** Read-only lens rendering. Gestures belong to the simulator, never decision actions. */
export function LensStepCard({
  title,
  body,
  index,
  total,
}: {
  title: string;
  body?: string;
  index: number;
  total: number;
}) {
  return (
    <article className="glasses-step" data-component="LensCard" aria-label={title}>
      <header>
        <svg width="26" height="26" viewBox="0 0 64 64" aria-hidden="true">
          <g fill="currentColor">
            <circle cx="48.3" cy="15.7" r="5" />
            <circle cx="32" cy="9" r="5" />
            <circle cx="15.7" cy="15.7" r="5" />
            <circle cx="9" cy="32" r="5" />
            <circle cx="15.7" cy="48.3" r="5" />
            <circle cx="32" cy="55" r="5" />
            <circle cx="48.3" cy="48.3" r="5" />
          </g>
          <circle cx="32" cy="32" r="9" fill="#4D8DFF" />
        </svg>
        <span>
          Your step · {index + 1} of {total}
        </span>
      </header>
      <h2>{title}</h2>
      {body && <p>{body}</p>}
      <div className="glasses-progress" role="img" aria-label={`Step ${index + 1} of ${total}`}>
        {Array.from({ length: total }, (_, i) => i + 1).map((position) => (
          <span key={position} className={position <= index + 1 ? "on" : undefined} />
        ))}
      </div>
      <footer>Say “done” or “skip” · agents never press buttons</footer>
    </article>
  );
}
