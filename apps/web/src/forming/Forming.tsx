// SPDX-License-Identifier: Apache-2.0
// The screen after the first one. The same band carries on and the sentence becomes its headline;
// under it the host's chosen components arrive on a sheet framed like the map, so two sentences give
// two different screens. One question, who can find it, and then the Door.
import { useEffect, useRef, useState } from "react";
import { pinAtJoin } from "../chain/pin";
import { saveToken } from "../feed/config";
import {
  type Card,
  type DoorState,
  type Draft,
  type DraftReply,
  draftGoal,
  HostError,
  listPacks,
  openRoom,
  type PackInfo,
  type PackRef,
  type Reading,
  type Visibility,
} from "../genesis/api";
import { Composer } from "../genesis/Composer";
import { forgetStartCode, takeStartCode } from "../genesis/fragment";
import { markOwner } from "../genesis/owner";
import { PublicNav } from "../landing/PublicNav";
import { Door } from "./Door";
import { FormingCard, withEdits } from "./FormingCard";
import { Sentence } from "./Sentence";
import { seatTotal, WhoCanFind } from "./WhoCanFind";
import "../genesis/genesis.css";
import "../landing/landing.css";
import "./forming.css";

type Stage = "read" | "who" | "opening" | "door";

function refusal(e: unknown): string {
  if (e instanceof HostError) {
    if (e.status === 401) return "This host needs a start link to open a room.";
    if (e.status === 403 || e.status === 404)
      return "This host doesn't take new rooms from the web.";
    if (e.status === 429) return "Too many tries. Wait a minute.";
    if (e.status === 422) return `The host refused this room${e.detail ? `: ${e.detail}` : "."}`;
    return `The host answered ${e.status}.`;
  }
  return "The host could not be reached.";
}

function closesLine(draft: Draft): string {
  if (!draft.deadline) return "closes in a week";
  const when = new Date(draft.deadline);
  return `closes ${when.toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" })}`;
}

export function Forming({
  onEnter,
  initialGoal = "",
}: {
  onEnter: () => void;
  /** The sentence typed on the first screen, read as soon as this screen opens. */
  initialGoal?: string;
}) {
  const [goal, setGoal] = useState(initialGoal.trim());
  const [typing, setTyping] = useState(initialGoal.trim());
  const [changing, setChanging] = useState(!initialGoal.trim());
  const [reply, setReply] = useState<DraftReply | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [reading, setReading] = useState(Boolean(initialGoal.trim()));
  const [hot, setHot] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("read");
  const [visibility, setVisibility] = useState<Visibility>("code");
  const [error, setError] = useState("");
  const [opened, setOpened] = useState<{ token: string; door?: DoorState } | null>(null);
  const [packs, setPacks] = useState<PackInfo[]>([]);
  /** Undefined until the writer chooses; then the host's suggestion leads. */
  const [picked, setPicked] = useState<PackRef | null | undefined>(undefined);
  const asked = useRef<AbortController | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    listPacks(undefined, ctl.signal)
      .then(setPacks)
      .catch(() => {
        if (!ctl.signal.aborted) setPacks([]);
      });
    return () => ctl.abort();
  }, []);

  useEffect(() => {
    if (!goal) return;
    asked.current?.abort();
    const ctl = new AbortController();
    asked.current = ctl;
    setReading(true);
    setReply(null);
    setDraft(null);
    setStage("read");
    draftGoal(goal, ctl.signal, undefined, picked ?? null)
      .then((r) => {
        if (ctl.signal.aborted) return;
        setReply(r);
        setDraft(r.draft);
        setVisibility(r.draft.place ? "nearby" : "code");
        setError("");
        const hint = r.suggested;
        if (picked === undefined && hint) {
          setPicked({ name: hint.name, version: hint.version });
        }
      })
      .catch((e) => {
        if (!ctl.signal.aborted) setError(refusal(e));
      })
      .finally(() => {
        if (!ctl.signal.aborted) setReading(false);
      });
    return () => ctl.abort();
  }, [goal, picked]);

  const open = async () => {
    if (!draft) return;
    setStage("opening");
    try {
      const started = await openRoom({ ...draft, goal }, visibility, takeStartCode());
      forgetStartCode();
      saveToken(started.owner.token);
      markOwner(started.coalition_id);
      pinAtJoin(started.coalition_id, started.host_key);
      setOpened({ token: started.owner.token, door: started.door });
      globalThis.history.pushState(null, "", "/door");
      setStage("door");
    } catch (e) {
      setStage("who");
      setError(refusal(e));
    }
  };

  if (stage === "door" && opened) {
    return <Door token={opened.token} first={opened.door} onEnter={onEnter} />;
  }

  const cards: Card[] = reply?.composition?.cards ?? [];
  const same = (a: PackRef | null | undefined, b: PackRef) =>
    a?.name === b.name && a.version === b.version;
  const words = cards.map((c) => c.word).filter((w): w is string => Boolean(w));
  const spans: Reading[] = reply?.reading ?? [];
  const eyebrow = reading
    ? "The Gardener is reading"
    : reply
      ? `${reply.composition?.source === "model" ? "Read by the Gardener's model" : "Read without a model"} · ${cards.length} ${cards.length === 1 ? "component" : "components"} chosen`
      : "Opening a room";

  return (
    <div className="ld fm">
      <PublicNav onJoin={(secret) => globalThis.location.assign(`/join#${secret}`)} />
      <main>
        <section className="ld-hero fm-hero">
          <p className="ld-eyebrow" role="status">
            {eyebrow}
          </p>
          {goal && !changing ? (
            <h1 className="ld-title fm-sentence">
              <Sentence goal={goal} words={words} hot={hot} onHot={setHot} />
            </h1>
          ) : (
            <h1 className="ld-title">
              What needs doing, and with <em>whom?</em>
            </h1>
          )}
          {!changing && (
            <p className="ld-sub">
              {words.length > 0
                ? "Point at a word to see what it built. Nothing is public until you open it."
                : "Nothing is public until you open it."}
            </p>
          )}
          {changing && (
            <div className="ld-ask">
              <Composer
                value={typing}
                onChange={setTyping}
                reading={spans.length && typing === goal ? spans : []}
                busy={false}
                locked={false}
                canSubmit={Boolean(typing.trim())}
                onSubmit={() => {
                  setGoal(typing.trim());
                  setChanging(false);
                }}
              />
            </div>
          )}
          <div className="ld-tries fm-tries">
            {goal && !changing && (
              <button type="button" onClick={() => setChanging(true)}>
                Change the sentence
              </button>
            )}
            {packs.length > 0 && goal && (
              <>
                <span>Pack</span>
                {packs.map((p) => (
                  <button
                    key={`${p.name}@${p.version}`}
                    type="button"
                    aria-pressed={same(picked, p)}
                    onClick={() => setPicked({ name: p.name, version: p.version })}
                  >
                    {p.label ?? p.name}
                  </button>
                ))}
                <button type="button" aria-pressed={!picked} onClick={() => setPicked(null)}>
                  Plain language
                </button>
              </>
            )}
          </div>
        </section>
        <div className="ld-mapwrap fm-wrap">
          <div className="fm-board" data-dim={stage !== "read"} aria-busy={reading}>
            {reading &&
              ["hero", "half", "third"].map((size) => (
                <section key={size} className="fm-card" data-size={size}>
                  <div className="fm-skel">
                    <span className="ck-assemble-bar" style={{ width: "72%" }} />
                    <span className="ck-assemble-bar" style={{ width: "46%" }} />
                  </div>
                </section>
              ))}
            {!reading && !goal && (
              <p className="fm-empty">Say what needs doing, and a room forms around it here.</p>
            )}
            {draft &&
              cards.map((card, i) => (
                <FormingCard
                  key={card.id}
                  card={withEdits(card, draft)}
                  draft={draft}
                  delay={i * 340}
                  hot={Boolean(card.word && card.word === hot)}
                  onHot={setHot}
                  onEdit={(patch) => setDraft({ ...draft, ...patch })}
                />
              ))}
          </div>
        </div>
        {error && (
          <p className="fm-error" role="alert">
            {error}
          </p>
        )}
        {draft && stage === "read" && (
          <div className="fm-bar">
            <div className="fm-bar-in">
              <p>
                <b>{seatTotal(draft)} seats</b> · {closesLine(draft)}. Change anything above.
              </p>
              <button type="button" className="fm-go" onClick={() => setStage("who")}>
                Looks right
              </button>
            </div>
          </div>
        )}
        {draft && stage !== "read" && (
          <div className="fm-bar">
            <WhoCanFind
              draft={{ ...draft, goal }}
              value={visibility}
              busy={stage === "opening"}
              onChange={setVisibility}
              onBack={() => setStage("read")}
              onOpen={open}
            />
          </div>
        )}
      </main>
    </div>
  );
}
