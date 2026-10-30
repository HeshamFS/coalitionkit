// SPDX-License-Identifier: Apache-2.0
import type { TextareaHTMLAttributes } from "react";
import { type Props, rows, str } from "./shared";

export function Textarea({
  common,
  p,
}: {
  common: TextareaHTMLAttributes<HTMLTextAreaElement>;
  p: Props;
}) {
  const decorations = rows(p.decorations).filter((d) => str(d.text));
  const text = str(common.value);
  const pieces: { text: string; kind?: string; start: number }[] = [];
  let at = 0;
  while (at < text.length) {
    const match = decorations
      .map((d) => ({ d, start: text.indexOf(str(d.text), at) }))
      .filter((m) => m.start >= at)
      .sort((a, b) => a.start - b.start)[0];
    if (!match) {
      pieces.push({ text: text.slice(at), start: at });
      break;
    }
    if (match.start > at) pieces.push({ text: text.slice(at, match.start), start: at });
    pieces.push({ text: str(match.d.text), kind: str(match.d.kind), start: match.start });
    at = match.start + str(match.d.text).length;
  }
  if (!decorations.length)
    return <textarea {...common} rows={3} placeholder={str(p.placeholder)} />;
  return (
    <div className="f01-decorated-textarea">
      <textarea {...common} rows={3} placeholder={str(p.placeholder)} />
      <div className="f01-textarea-preview" aria-hidden="true">
        {pieces.map((piece) =>
          piece.kind === "bold" ? (
            <b key={piece.start}>{piece.text}</b>
          ) : piece.kind === "mention" ? (
            <span className="chip chip-on" key={piece.start}>
              {piece.text}
            </span>
          ) : (
            <span key={piece.start}>{piece.text}</span>
          ),
        )}
      </div>
    </div>
  );
}
