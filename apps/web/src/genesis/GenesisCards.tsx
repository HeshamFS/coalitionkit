// SPDX-License-Identifier: Apache-2.0
// The cards that germinate beside the table as the Gardener reads the goal (board: Genesis).
// Every card is editable in place until the coalition starts (story J-02).
import { useState } from "react";
import { QrCard } from "../door/QrCard";
import { capital, makeWord, type WordFn } from "../feed/vocabulary";
import { Assemble } from "../ui/Assemble";
import type { Draft, Invitation, PackInfo, PackRef, Role, Suggestion } from "./api";

const ROLE_ID = /[^a-z0-9-]+/g;

function roleId(label: string, taken: Set<string>): string {
  const base =
    label
      .toLowerCase()
      .replace(ROLE_ID, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "member";
  let id = base;
  for (let i = 2; taken.has(id); i++) id = `${base}-${i}`;
  return id;
}

export function seatCount(draft: Draft | null): number {
  if (!draft) return 0;
  return draft.roles.reduce((n, r) => n + Math.max(1, r.count ?? 1), 0);
}

export function SeatsCard({
  draft,
  locked,
  onEdit,
}: {
  draft: Draft | null;
  locked: boolean;
  onEdit: (roles: Role[]) => void;
}) {
  const roles = draft?.roles ?? [];
  const set = (i: number, patch: Partial<Role>) =>
    onEdit(roles.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return (
    <section className="gn-card" aria-label="Seats it found">
      <Assemble ready={draft !== null} label="Seats it found" delay={0}>
        <span className="gn-card-k">Seats it found</span>
        <ul className="gn-roles">
          {roles.map((r, i) => (
            <li key={r.id}>
              <input
                className="gn-count"
                type="number"
                min={1}
                max={500}
                aria-label={`How many ${r.label}`}
                value={r.count ?? 1}
                readOnly={locked}
                onChange={(e) => set(i, { count: Math.max(1, Number(e.target.value) || 1) })}
              />
              <input
                className="gn-inline"
                aria-label="Seat name"
                value={r.label}
                readOnly={locked}
                maxLength={64}
                onChange={(e) => set(i, { label: e.target.value })}
              />
              {!locked && roles.length > 1 && (
                <button
                  type="button"
                  className="gn-x"
                  aria-label={`Remove ${r.label}`}
                  onClick={() => onEdit(roles.filter((_, j) => j !== i))}
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
        {!locked && (
          <button
            type="button"
            className="gn-add"
            onClick={() => {
              const taken = new Set(roles.map((r) => r.id));
              onEdit([...roles, { id: roleId("seat", taken), label: "new seat", count: 1 }]);
            }}
          >
            + Add a kind of seat
          </button>
        )}
        <span className="gn-card-meta">roles read from your sentence</span>
      </Assemble>
    </section>
  );
}

export function NeedsCard({
  draft,
  locked,
  onEdit,
  word = makeWord({}),
}: {
  draft: Draft | null;
  locked: boolean;
  onEdit: (needs: string[]) => void;
  word?: WordFn;
}) {
  const heading = capital(word("need", 2));
  const [adding, setAdding] = useState("");
  const needs = draft?.needs ?? [];
  return (
    <section className="gn-card" aria-label={heading}>
      <Assemble ready={draft !== null} label={heading} delay={180}>
        <span className="gn-card-k">{heading}</span>
        {needs.length === 0 && <span className="gn-card-meta">None read yet. Add one below.</span>}
        <ul className="gn-needs">
          {needs.map((n, i) => (
            <li key={`${n}-${i.toString()}`}>
              <span>{n}</span>
              {!locked && (
                <button
                  type="button"
                  className="gn-x"
                  aria-label={`Remove need: ${n}`}
                  onClick={() => onEdit(needs.filter((_, j) => j !== i))}
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
        {!locked && (
          <form
            className="gn-add-need"
            onSubmit={(e) => {
              e.preventDefault();
              if (adding.trim()) onEdit([...needs, adding.trim()]);
              setAdding("");
            }}
          >
            <label className="sr-only" htmlFor="gn-need">
              Add a need
            </label>
            <input
              id="gn-need"
              className="gn-inline"
              placeholder="+ Add a need"
              value={adding}
              maxLength={120}
              onChange={(e) => setAdding(e.target.value)}
            />
          </form>
        )}
      </Assemble>
    </section>
  );
}

function localInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function DeadlineCard({
  draft,
  locked,
  onEdit,
}: {
  draft: Draft | null;
  locked: boolean;
  onEdit: (deadline: string | null) => void;
}) {
  const when = draft?.deadline ? new Date(draft.deadline) : null;
  return (
    <section className="gn-card" aria-label="Deadline">
      <Assemble ready={draft !== null} label="Deadline" delay={360}>
        <span className="gn-card-k">Deadline</span>
        <span className="gn-card-v">
          {when
            ? when.toLocaleString(undefined, {
                weekday: "short",
                day: "numeric",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
              })
            : "None said · one week from start"}
        </span>
        {!locked && (
          <>
            <label className="sr-only" htmlFor="gn-deadline">
              Change the deadline
            </label>
            <input
              id="gn-deadline"
              className="gn-inline"
              type="datetime-local"
              value={localInput(draft?.deadline ?? null)}
              onChange={(e) =>
                onEdit(e.target.value ? new Date(e.target.value).toISOString() : null)
              }
            />
          </>
        )}
      </Assemble>
    </section>
  );
}

export function PackCard({
  draft,
  packs = [],
  chosen = null,
  suggested = null,
  locked = false,
  onChoose,
}: {
  draft: Draft | null;
  /** The packs the host has installed. */
  packs?: PackInfo[];
  /** The pack in use for the draft; null is plain language. */
  chosen?: PackRef | null;
  suggested?: Suggestion | null;
  locked?: boolean;
  onChoose?: (pack: PackRef | null) => void;
}) {
  const same = (a: PackRef | null, b: PackRef) => a?.name === b.name && a.version === b.version;
  const why = suggested && same(chosen, suggested) ? suggested.why.join(", ") : "";
  return (
    <section className="gn-card" aria-label="Discipline pack">
      <Assemble ready={draft !== null} label="Discipline pack" delay={540}>
        <span className="gn-card-k">Discipline pack</span>
        <div className="gn-chips">
          {packs.map((p) => (
            <button
              key={`${p.name}@${p.version}`}
              type="button"
              className="gn-chip"
              data-on={same(chosen, p)}
              aria-pressed={same(chosen, p)}
              disabled={locked}
              onClick={() => onChoose?.({ name: p.name, version: p.version })}
            >
              {p.label ?? p.name}
            </button>
          ))}
          {packs.length === 0 ? (
            <span className="gn-chip" data-on={!chosen}>
              No pack: plain language
            </span>
          ) : (
            <button
              type="button"
              className="gn-chip"
              data-on={!chosen}
              aria-pressed={!chosen}
              disabled={locked}
              onClick={() => onChoose?.(null)}
            >
              No pack: plain language
            </button>
          )}
        </div>
        <span className="gn-card-meta">
          {packs.length === 0
            ? "Packs add words, roles and know-how on top. None is installed on this host."
            : why
              ? `Suggested because: ${why}. You can choose no pack.`
              : "Packs add words, roles and know-how on top. Choosing one re-reads your sentence with its seats and words."}
        </span>
      </Assemble>
    </section>
  );
}

export function InviteCard({
  started,
  invitations,
  busy,
  mcpUrl,
  goal,
  seats,
  onInvite,
}: {
  started: boolean;
  invitations: Invitation[];
  busy: boolean;
  mcpUrl: string;
  goal: string;
  seats: number;
  onInvite: (kind: Invitation["kind"]) => void;
}) {
  const [copied, setCopied] = useState("");
  const [held, setHeld] = useState<Invitation | null>(null);
  const copy = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
    } catch {
      setCopied("");
    }
  };
  return (
    <section className="gn-card" aria-label="Invite, any agent">
      <Assemble ready label="Invite, any agent" delay={720}>
        <span className="gn-card-k">Invite, any agent</span>
        <div className="gn-chips">
          <button
            type="button"
            className="gn-chip"
            disabled={!started || busy}
            onClick={() => onInvite("member")}
          >
            Link for a person
          </button>
          <button
            type="button"
            className="gn-chip"
            disabled={!started || busy}
            onClick={() => onInvite("business")}
          >
            A2A card for a business
          </button>
          <button
            type="button"
            className="gn-chip"
            disabled={!started}
            onClick={() => copy(mcpUrl, "mcp")}
            title="Add this address as a connector in Claude or ChatGPT, then open a person's link there"
          >
            {copied === "mcp" ? "Copied" : "Claude · ChatGPT"}
          </button>
        </div>
        {!started && <span className="gn-card-meta">Opens when the coalition starts.</span>}
        <ul className="gn-links">
          {invitations.map((inv) => (
            <li key={inv.id}>
              <span className="gn-link-kind">
                {inv.kind === "business" ? "business" : "person"}
              </span>
              <code>{inv.link.replace(/#.*/, "#••••")}</code>
              <button type="button" className="gn-chip" onClick={() => copy(inv.link, inv.id)}>
                {copied === inv.id ? "Copied" : "Copy"}
              </button>
              {inv.kind === "member" && (
                <button type="button" className="gn-chip" onClick={() => setHeld(inv)}>
                  QR
                </button>
              )}
            </li>
          ))}
        </ul>
      </Assemble>
      {held && <QrCard link={held.link} goal={goal} seats={seats} onClose={() => setHeld(null)} />}
    </section>
  );
}
