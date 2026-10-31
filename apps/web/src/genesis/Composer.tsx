// SPDX-License-Identifier: Apache-2.0
// The one input on the first screen. What the Gardener read is underlined in place, so the owner
// sees which words became seats, needs and the deadline.
import { useEffect, useRef, useState } from "react";
import type { Reading } from "./api";

type Recognition = {
  lang: string;
  interimResults: boolean;
  onresult: (e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void;
  onend: () => void;
  start: () => void;
  stop: () => void;
};

function recognizer(): (new () => Recognition) | undefined {
  const w = globalThis as unknown as {
    SpeechRecognition?: new () => Recognition;
    webkitSpeechRecognition?: new () => Recognition;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}

function marked(text: string, reading: Reading[]) {
  const spans = [...reading]
    .filter((r) => r.span[0] >= 0 && r.span[1] <= text.length && r.span[0] < r.span[1])
    .sort((a, b) => a.span[0] - b.span[0]);
  const out: (string | { text: string; kind: string })[] = [];
  let at = 0;
  for (const r of spans) {
    if (r.span[0] < at) continue;
    out.push(text.slice(at, r.span[0]));
    out.push({ text: text.slice(r.span[0], r.span[1]), kind: r.kind });
    at = r.span[1];
  }
  out.push(text.slice(at));
  return out;
}

export function Composer({
  value,
  onChange,
  reading,
  onSubmit,
  busy,
  locked,
}: {
  value: string;
  onChange: (v: string) => void;
  reading: Reading[];
  onSubmit: () => void;
  busy: boolean;
  locked: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const mirror = useRef<HTMLDivElement>(null);
  const [listening, setListening] = useState(false);
  const rec = useRef<Recognition | null>(null);
  const Speech = recognizer();
  useEffect(() => {
    if (!locked) input.current?.focus();
  }, [locked]);
  const sync = () => {
    if (mirror.current && input.current) mirror.current.scrollLeft = input.current.scrollLeft;
  };
  const submit = (e: { preventDefault: () => void }) => {
    e.preventDefault();
    if (value.trim() && !locked) onSubmit();
  };
  const listen = () => {
    if (!Speech) return;
    if (listening) {
      rec.current?.stop();
      return;
    }
    const r = new Speech();
    r.lang = navigator.language || "en";
    r.interimResults = true;
    r.onresult = (e) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) text += e.results[i]?.[0]?.transcript ?? "";
      onChange(text);
    };
    r.onend = () => setListening(false);
    rec.current = r;
    setListening(true);
    r.start();
  };
  return (
    <form className="gn-composer" onSubmit={submit} aria-label="Start a coalition">
      {Speech && (
        <button
          type="button"
          className="gn-mic"
          aria-pressed={listening}
          aria-label={listening ? "Stop listening" : "Say the goal"}
          onClick={listen}
          disabled={locked}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="8" y="3" width="8" height="12" rx="4" />
            <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
          </svg>
        </button>
      )}
      <div className="gn-field">
        <div className="gn-mirror" ref={mirror} aria-hidden="true">
          {marked(value, reading).map((part, i) =>
            typeof part === "string" ? (
              // biome-ignore lint/suspicious/noArrayIndexKey: parts are positional
              <span key={i}>{part}</span>
            ) : (
              // biome-ignore lint/suspicious/noArrayIndexKey: parts are positional
              <mark key={i} data-kind={part.kind}>
                {part.text}
              </mark>
            ),
          )}
        </div>
        <label htmlFor="gn-goal" className="sr-only">
          What should get done?
        </label>
        <input
          id="gn-goal"
          ref={input}
          value={value}
          maxLength={500}
          placeholder="What should get done, by when, and with whom?"
          autoComplete="off"
          spellCheck
          readOnly={locked}
          onChange={(e) => onChange(e.target.value)}
          onScroll={sync}
          onKeyUp={sync}
        />
      </div>
      {busy && (
        <span className="gn-reading-dot" role="status" aria-label="The Gardener is reading" />
      )}
      <button
        type="submit"
        className="gn-send"
        aria-label="Set the goal"
        disabled={!value.trim() || locked}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </button>
    </form>
  );
}
