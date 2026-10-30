// SPDX-License-Identifier: Apache-2.0
import { Frame, list, obj, type Props, str } from "../f05/shared";

/** Structured answers retain their receipt and choices without exposing vault contents. */
export function AnswerCard({ p }: Props) {
  const answer = p.answer;
  const detail = obj(answer);
  const state =
    answer === undefined || detail.state === "waiting"
      ? "waiting"
      : answer === null
        ? "declined"
        : "answered";
  const choices = list(detail.choices);
  const selected = str(detail.value ?? answer);
  return (
    <Frame
      name="AnswerCard"
      state={state}
      className={`card f06-answer-card ${state === "waiting" ? "card-dashed" : ""}`}
    >
      <span className="st">
        {str(p.kind).replaceAll("-", " ")} · {state === "waiting" ? "to" : "from"} {str(p.from)}
        {state === "waiting" && detail.waited != null && ` · waiting ${str(detail.waited)} min`}
      </span>
      <span className={`small ${state === "answered" ? "f06-query" : ""}`}>“{str(p.query)}”</span>
      {state === "answered" &&
        (p.kind === "choice" ? (
          <div className="row wrap">
            {(choices.length ? choices : [selected]).map((choice) => (
              <span
                key={str(choice)}
                className={`chip ${str(choice) === selected ? "chip-on" : ""}`}
              >
                {str(choice)}
                {str(choice) === selected ? " ✓" : ""}
              </span>
            ))}
          </div>
        ) : (
          <div className="row">
            <span className="answer f06-answer">
              {p.kind === "number-range"
                ? `${str(detail.min)} – ${str(detail.max)} ${str(detail.unit)}`
                : str(detail.value ?? answer)}
            </span>
            {p.kind === "number-range" && (
              <span className="h-right badge b-estimate">range only</span>
            )}
            {detail.event_ref != null && (
              <span className="h-right st" title={str(detail.event_ref)}>
                #{str(detail.event_ref).split(":").at(-1)}
              </span>
            )}
          </div>
        ))}
      {state === "declined" && <span className="small">Declined</span>}
    </Frame>
  );
}
