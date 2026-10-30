// SPDX-License-Identifier: Apache-2.0
import { list, num, obj, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f10.css";

export function MintPipeline({ p, send }: { p: Props; send: Send }) {
  const stages = rows(p.stages);
  return (
    <>
      <div className="f10-stages">
        {stages.map((stage, i) => (
          <button
            type="button"
            aria-label={`Open ${text(list(stage.artifacts)[0]) || text(stage.name)}`}
            onClick={() => send("stage.open", { artifact: list(stage.artifacts)[0] ?? stage.name })}
            className={`card f10-stage ${stage.state === "done" ? "f10-stage-done" : stage.state === "running" ? "card-live" : ""}`}
            key={text(stage.name)}
          >
            <span className="row">
              {stage.state === "done" ? (
                <svg className="ico ico-sm family-ok" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 12l5 5 9-10" />
                </svg>
              ) : stage.state === "running" ? (
                <span className="spinner f10-test-running" />
              ) : (
                <span className="f10-stage-space" />
              )}
              <b>{text(stage.name)}</b>
            </span>
            <span className="st">{text(stage.detail)}</span>
            <span className="num small">
              {stage.state === "running"
                ? "running"
                : stage.state === "waiting"
                  ? "next"
                  : i === 0
                    ? "—"
                    : `${text(stage.took)} s`}
            </span>
          </button>
        ))}
      </div>
      <div className="f10-stage-meter">
        {stages
          .filter((s) => s.state === "done")
          .map((s) => (
            <span key={text(s.name)} style={{ width: `${num(s.took)}%` }} />
          ))}
      </div>
      <div className="f10-artifacts">
        {stages
          .filter((s) => s.preview)
          .map((s) => {
            const preview = obj(s.preview);
            return (
              <button
                type="button"
                key={text(s.name)}
                className={`stage f10-artifact ${preview.kind === "spec" ? "f10-spec" : ""}`}
                onClick={() => send("stage.open", { artifact: list(s.artifacts)[0] })}
              >
                <span className="eyebrow">{text(preview.title)}</span>
                {preview.kind === "masks" && (
                  <div className="row f10-thumbnails">
                    {rows(preview.frames).map((frame, i) => (
                      <svg
                        key={text(frame.label)}
                        viewBox="0 0 56 42"
                        role="img"
                        aria-label={text(frame.label)}
                      >
                        <rect
                          x={10 + i * 3}
                          y={10 - i * 2}
                          width={22 + i * 4}
                          height={14 + i * 8}
                          fill="none"
                          stroke="var(--dark-blue)"
                          strokeWidth="1.5"
                        />
                        {i === 0 && (
                          <circle
                            cx="42"
                            cy="16"
                            r="5"
                            fill="none"
                            stroke="var(--f10-mask-dial)"
                            strokeWidth="1.5"
                          />
                        )}
                      </svg>
                    ))}
                  </div>
                )}
                {list(preview.lines).map((line) => (
                  <span key={text(line)} className={preview.kind === "code" ? "mono small" : "st"}>
                    {text(line)}
                  </span>
                ))}
                {Boolean(preview.footer) && <span className="st">{text(preview.footer)}</span>}
              </button>
            );
          })}
      </div>
      <div className="row small">
        <span>
          Elapsed <b className="num">{text(p.elapsed)} s</b>
        </span>
        <span className="grow">{text(stages.find((s) => s.runtime)?.runtime)}</span>
        <span className="badge b-estimate">{text(p.cost)}</span>
      </div>
    </>
  );
}
