// SPDX-License-Identifier: Apache-2.0
// Answer a question by speaking or with a photo. The host reads it into the question's own closed
// kind and says it in words; nothing is saved until the person presses "Use this answer", which
// posts it through the same brief route as the question's own Send button.
import { useMemo, useState } from "react";
import { problemText } from "../api";
import { useTable } from "../context";
import type { BriefItem, Room } from "../room";
import { slotLabel } from "../slots";
import { CameraButton, MicButton } from "./Buttons";
import { type InputsIo, inputsIo, type Reading } from "./io";

type Proposal = Reading & { via: "voice" | "photo" };

/** Time slots in the viewer's own time, as the question's chips show them; else the host's words. */
export function wordsFor(answer: unknown, words: string, slots: Room["slots"]): string {
  if (!Array.isArray(answer)) return words;
  const found = answer.map((id) => slots.find((s) => s.id === id));
  return found.every((s) => s?.start)
    ? found.map((s) => (s ? slotLabel(s) : "")).join(", ")
    : words;
}

export function BriefInputs({ item, io: given }: { item: BriefItem; io?: InputsIo }) {
  const { io: room, room: here } = useTable();
  const io = useMemo(() => given ?? inputsIo(), [given]);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [edited, setEdited] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");
  const free = item.component === "TextArea";

  async function read(via: Proposal["via"], blob: Blob) {
    setProblem("");
    setBusy(true);
    const r = via === "voice" ? await io.voice(blob, item.id) : await io.photo(blob, item.id);
    setBusy(false);
    if (!r.ok) return setProblem(problemText(r));
    setProposal({ ...r.data, via });
    setEdited(r.data.words);
  }

  async function confirm() {
    if (!proposal || proposal.answer === null) return;
    const value = free ? edited.trim() : proposal.answer;
    if (value === "") return;
    setBusy(true);
    const r = await room.brief(item.id, { value });
    setBusy(false);
    if (!r.ok) return setProblem(problemText(r));
    setProposal(null);
  }

  const found = proposal !== null && proposal.answer !== null;
  return (
    <div className="ck-in-brief">
      <span className="ck-in-hint">Or answer by</span>
      <MicButton
        label="Answer by voice"
        disabled={busy}
        onClip={(wav) => void read("voice", wav)}
        onProblem={setProblem}
      />
      <CameraButton
        label="Answer with a photo"
        disabled={busy}
        onImage={(image) => void read("photo", image)}
      />
      {busy && !proposal && (
        <p className="ck-in-note" role="status">
          Your agent is reading it…
        </p>
      )}
      {problem && (
        <p className="ck-in-note" role="alert">
          {problem}
        </p>
      )}
      {proposal && (
        <section className="ck-in-confirm" aria-label="Check the answer before it is saved">
          <span className="tb-tag">
            {proposal.via === "voice" ? "You said" : "Your photo shows"}
          </span>
          <p className="ck-in-seen">
            {proposal.via === "voice" ? `“${proposal.text}”` : proposal.description}
          </p>
          {found ? (
            free ? (
              <textarea
                aria-label="Your answer"
                value={edited}
                maxLength={300}
                rows={2}
                onChange={(e) => setEdited(e.target.value)}
              />
            ) : (
              <p className="ck-in-answer">
                Your answer: <b>{wordsFor(proposal.answer, proposal.words, here.slots)}</b>
              </p>
            )
          ) : (
            <p className="ck-in-answer">
              That does not answer this question. Try again, or answer above.
            </p>
          )}
          <div className="ck-in-row">
            {found && (
              <button
                type="button"
                className="btn"
                disabled={busy || (free && !edited.trim())}
                onClick={() => void confirm()}
              >
                Use this answer
              </button>
            )}
            <button type="button" className="tb-linky" onClick={() => setProposal(null)}>
              {found ? "Not this" : "Close"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
