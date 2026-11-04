// SPDX-License-Identifier: Apache-2.0
// Say it by voice, or show it with a photo. The host reads the clip or photo into words; the person
// sees them, may change them, and only "Say it" sends them down the same route as the say box.
import { useMemo, useState } from "react";
import { problemText } from "../api";
import { useTable } from "../context";
import { CameraButton, MicButton } from "./Buttons";
import { type InputsIo, inputsIo } from "./io";

type Draft = { text: string; via: "voice" | "photo"; seen: string };

/** `locked` is true while the say box itself is closed. */
export function SayInputs({ locked, io: given }: { locked: boolean; io?: InputsIo }) {
  const { setSaid } = useTable();
  const io = useMemo(() => given ?? inputsIo(), [given]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState<"" | "reading" | "sending">("");
  const [problem, setProblem] = useState("");

  async function read(via: Draft["via"], blob: Blob) {
    setProblem("");
    setBusy("reading");
    const r = via === "voice" ? await io.voice(blob) : await io.photo(blob);
    setBusy("");
    if (!r.ok) return setProblem(problemText(r));
    const text = r.data.text.trim();
    if (!text) return setProblem("Nothing could be read from that. Try again, or type it.");
    setDraft({ text, via, seen: via === "photo" ? r.data.description : "" });
  }

  async function confirm() {
    if (!draft) return;
    const text = draft.text.trim();
    if (!text) return;
    setBusy("sending");
    const r = await io.say(text, draft.via);
    setBusy("");
    if (!r.ok) return setProblem(problemText(r));
    setSaid({ text, reply: r.data });
    setDraft(null);
  }

  return (
    <>
      <MicButton
        label="Say it by voice"
        disabled={locked || busy !== ""}
        onClip={(wav) => void read("voice", wav)}
        onProblem={setProblem}
      />
      <CameraButton
        label="Show it with a photo"
        disabled={locked || busy !== ""}
        onImage={(image) => void read("photo", image)}
      />
      {busy === "reading" && (
        <p className="ck-in-note" role="status">
          Your agent is reading it…
        </p>
      )}
      {problem && (
        <p className="ck-in-note" role="alert">
          {problem}
        </p>
      )}
      {draft && (
        <section className="ck-in-confirm" aria-label="Check the words before they go">
          <span className="tb-tag">
            {draft.via === "voice" ? "You said, as your agent heard it" : "From your photo"}
          </span>
          {draft.seen && <p className="ck-in-seen">{draft.seen}</p>}
          <textarea
            aria-label="The words to send"
            value={draft.text}
            maxLength={500}
            rows={2}
            onChange={(e) => setDraft({ ...draft, text: e.target.value })}
          />
          <div className="ck-in-row">
            <button
              type="button"
              className="btn"
              disabled={busy !== "" || !draft.text.trim()}
              onClick={() => void confirm()}
            >
              {busy === "sending" ? "Sending…" : "Say it"}
            </button>
            <button type="button" className="tb-linky" onClick={() => setDraft(null)}>
              Drop it
            </button>
          </div>
        </section>
      )}
    </>
  );
}
