// SPDX-License-Identifier: Apache-2.0
// The first screen (board: Genesis, story J-01 to J-03). Type or say a goal; the Gardener reads it
// live, seats arrive at the table and the draft germinates beside it; Start creates the coalition.
import { useEffect, useRef, useState } from "react";
import { saveToken } from "../feed/config";
import {
  type Draft,
  type DraftReply,
  draftGoal,
  HostError,
  type Invitation,
  invite,
  type Reading,
  startCoalition,
} from "./api";
import { Composer } from "./Composer";
import { forgetStartCode, takeStartCode } from "./fragment";
import {
  DeadlineCard,
  InviteCard,
  NeedsCard,
  PackCard,
  SeatsCard,
  seatCount,
} from "./GenesisCards";
import { TableMark } from "./TableMark";
import "./genesis.css";

type Phase = "idle" | "starting" | "started";

const READ_AFTER_MS = 650;

function refusal(e: unknown): string {
  if (e instanceof HostError) {
    if (e.status === 401)
      return "The start link has been used or has expired. Run coalitionkit up for a new one.";
    if (e.status === 403 || e.status === 404)
      return "This host does not take new coalitions from the web.";
    if (e.status === 429) return "Too many tries. Wait a minute.";
    if (e.status === 422) return `The host refused this charter${e.detail ? `: ${e.detail}` : "."}`;
    return `The host answered ${e.status}.`;
  }
  return "The host could not be reached.";
}

export function Genesis({ onEnter, notice }: { onEnter: () => void; notice?: string }) {
  const [goal, setGoal] = useState("");
  const [reply, setReply] = useState<DraftReply | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [edited, setEdited] = useState(false);
  const [reading, setReading] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState(notice ?? "");
  const [owner, setOwner] = useState("");
  const [invites, setInvites] = useState<Invitation[]>([]);
  const [inviting, setInviting] = useState(false);
  const [startCode] = useState(() => takeStartCode());
  const asked = useRef<AbortController | null>(null);

  useEffect(() => {
    if (edited || phase !== "idle") return;
    const text = goal.trim();
    if (!text) {
      setReply(null);
      setDraft(null);
      return;
    }
    const timer = window.setTimeout(async () => {
      asked.current?.abort();
      const ctl = new AbortController();
      asked.current = ctl;
      setReading(true);
      try {
        const r = await draftGoal(text, ctl.signal);
        if (ctl.signal.aborted) return;
        setReply(r);
        setDraft(r.draft);
        setError("");
      } catch (e) {
        if (!ctl.signal.aborted) setError(refusal(e));
      } finally {
        if (!ctl.signal.aborted) setReading(false);
      }
    }, READ_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [goal, edited, phase]);

  const edit = (patch: Partial<Draft>) => {
    if (!draft) return;
    setEdited(true);
    setDraft({ ...draft, ...patch });
  };

  const start = async () => {
    if (!draft || !startCode) return;
    setPhase("starting");
    try {
      const started = await startCoalition({ ...draft, goal: goal.trim() }, startCode);
      forgetStartCode();
      saveToken(started.owner.token);
      setOwner(started.owner.token);
      setPhase("started");
      setError("");
    } catch (e) {
      setPhase("idle");
      setError(refusal(e));
    }
  };

  const addInvite = async (kind: Invitation["kind"]) => {
    setInviting(true);
    try {
      const r = await invite(owner, kind);
      setInvites((xs) => [...xs, ...r.invitations]);
    } catch (e) {
      setError(refusal(e));
    } finally {
      setInviting(false);
    }
  };

  const locked = phase !== "idle";
  const spans: Reading[] = edited ? [] : (reply?.reading ?? []);
  const mcpUrl = `${globalThis.location.origin}/mcp`;

  return (
    <main className="gn-stage" aria-labelledby="gn-title">
      <header className="gn-head">
        <p className="gn-eyebrow">The first screen · zero-pack</p>
        <h1 id="gn-title" className="gn-title">
          Type a goal. <em>Watch a coalition form.</em>
        </h1>
      </header>

      <div className="gn-grid">
        <div className="gn-col">
          <SeatsCard draft={draft} locked={locked} onEdit={(roles) => edit({ roles })} />
          <NeedsCard draft={draft} locked={locked} onEdit={(needs) => edit({ needs })} />
          <DeadlineCard draft={draft} locked={locked} onEdit={(deadline) => edit({ deadline })} />
        </div>
        <div className="gn-centre">
          <TableMark filled={seatCount(draft)} lit={phase === "started"} reading={reading} />
          <div className="gn-status" role="status" aria-live="polite">
            {phase === "started" ? (
              <span className="gn-pill" data-tone="live">
                <span className="gn-dot" />
                Goal set · the Gardener is drafting the first plans
              </span>
            ) : phase === "starting" ? (
              <span className="gn-pill">Starting the coalition…</span>
            ) : reading ? (
              <span className="gn-pill">The Gardener is reading</span>
            ) : reply ? (
              <span className="gn-pill">
                {edited
                  ? "Edited by you"
                  : reply.source === "model"
                    ? "Read by the Gardener's model"
                    : "Read without a model"}
                {edited && (
                  <button type="button" className="gn-link" onClick={() => setEdited(false)}>
                    Read the sentence again
                  </button>
                )}
              </span>
            ) : null}
          </div>
          {phase === "started" && (
            <button type="button" className="gn-enter" onClick={onEnter}>
              Enter the room
            </button>
          )}
        </div>
        <div className="gn-col">
          <PackCard draft={draft} />
          <InviteCard
            started={phase === "started"}
            invitations={invites}
            busy={inviting}
            mcpUrl={mcpUrl}
            onInvite={addInvite}
          />
        </div>
      </div>

      <div className="gn-bottom">
        {error && (
          <p className="gn-error" role="alert">
            {error}
          </p>
        )}
        <Composer
          value={goal}
          onChange={(v) => {
            setGoal(v);
            if (!v.trim()) setEdited(false);
          }}
          reading={spans}
          onSubmit={start}
          busy={reading}
          locked={locked}
          canSubmit={Boolean(startCode && draft)}
        />
        <p className="gn-foot">
          {startCode || phase === "started" ? (
            <>
              No screen here was designed in advance. Whatever you ask for, this table rebuilds
              around it.
            </>
          ) : (
            <>
              Starting needs the link that <code>coalitionkit up</code> prints. You can still type
              to see what the Gardener reads.{" "}
            </>
          )}{" "}
          <a href="/signin">Have a token? Sign in</a>
        </p>
      </div>
    </main>
  );
}
