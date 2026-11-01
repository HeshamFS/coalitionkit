// SPDX-License-Identifier: Apache-2.0
// My part, for a pack Coalition whose pack adds fields to offers: choose a need, fill the pack's
// public fields (sent as the offer's `ext` by your own agent), and keep its private fields in your
// own vault. Fields come only from the pack's schema the host delivered for this viewer.
import { useEffect, useId, useState } from "react";
import { Field } from "../components/f04/fields";
import type { ViewerState } from "../feed/delta";
import { eventsOf } from "../feed/derive";
import { ActionError, saveVault, sendOffer, vaultKeys } from "./agentActions";
import { fieldsOf, flatten, type JsonSchema, type Values } from "./extSchema";
import { SchemaForm } from "./schemaForm";

/** The pack's offer schema from the feed's `pack` key, when the pack adds offer fields. */
export function offerSchema(state: ViewerState | null): JsonSchema | null {
  const pack = (state as { pack?: { schemas?: { offer?: unknown } } } | null)?.pack;
  const schema = pack?.schemas?.offer;
  return schema && typeof schema === "object" ? (schema as JsonSchema) : null;
}

/** The schema without its private fields: those are asked for once, in the vault form. */
export function publicSchema(schema: JsonSchema): JsonSchema {
  const flat = flatten(schema);
  const properties = Object.fromEntries(
    Object.entries(flat.properties ?? {}).filter(([, p]) => p["x-private"] !== true),
  );
  const required = (flat.required ?? []).filter((key) => key in properties);
  return { ...flat, properties, required };
}

/** Needs the viewer can see, newest last, as {id, label}. */
export function openNeeds(state: ViewerState | null): { id: string; label: string }[] {
  return eventsOf(state)
    .filter((e) => e.type === "coalition.need" && typeof e.payload.need_id === "string")
    .map((e) => ({
      id: String(e.payload.need_id),
      label: typeof e.payload.description === "string" ? e.payload.description : "a need",
    }));
}

function explain(error: unknown): string {
  if (error instanceof ActionError) {
    if (error.status === 409) return "Your own agent sends offers for you, outside this page.";
    if (error.status === 422) return "The host refused these values. Check the fields.";
    return `The host refused (${error.status}).`;
  }
  return "The host could not be reached.";
}

function VaultForm({ schema }: { schema: JsonSchema }) {
  const heading = useId();
  const fields = fieldsOf(schema).filter((f) => f.private);
  const [values, setValues] = useState<Values>({});
  const [saved, setSaved] = useState<string[]>([]);
  const [note, setNote] = useState("");
  useEffect(() => {
    if (fields.length === 0) return;
    vaultKeys().then(
      (r) => setSaved(r.keys ?? []),
      () => setSaved([]),
    );
  }, [fields.length]);
  if (fields.length === 0) return null;
  return (
    <form
      className="room-panel room-ext"
      aria-labelledby={heading}
      onSubmit={(e) => {
        e.preventDefault();
        saveVault(values).then(
          () => {
            setSaved((old) => [...new Set([...old, ...Object.keys(values)])]);
            setNote("Kept in your vault. Nobody else sees these values.");
            setValues({});
          },
          (error) => setNote(explain(error)),
        );
      }}
    >
      <h2 id={heading}>Private to you</h2>
      {fields.map((f) => (
        <Field
          key={f.key}
          field={{
            label: saved.includes(f.key) ? `${f.title} (saved)` : f.title,
            kind: f.kind,
            required: false,
            private: "no",
            options: f.options,
            help: f.description,
          }}
          value={values[f.key]}
          change={(v) => setValues((old) => ({ ...old, [f.key]: v }))}
        />
      ))}
      {note && (
        <p className="small" role="status">
          {note}
        </p>
      )}
      <button type="submit" className="btn" disabled={Object.keys(values).length === 0}>
        Keep in my vault
      </button>
    </form>
  );
}

export function OfferPanel({ state }: { state: ViewerState | null }) {
  const schema = offerSchema(state);
  const needs = openNeeds(state);
  const [need, setNeed] = useState("");
  const [note, setNote] = useState("");
  const pick = useId();
  if (!schema || needs.length === 0) return null;
  const chosen = need || needs[needs.length - 1]?.id || "";
  return (
    <div className="room-stack">
      <div className="room-panel">
        <label htmlFor={pick} className="small">
          Offer for
        </label>
        <select
          id={pick}
          className="input"
          value={chosen}
          onChange={(e) => setNeed(e.target.value)}
        >
          {needs.map((n) => (
            <option key={n.id} value={n.id}>
              {n.label}
            </option>
          ))}
        </select>
      </div>
      <SchemaForm
        schema={publicSchema(schema)}
        submitLabel="Send through my agent"
        onSubmit={(ext) =>
          sendOffer(chosen, ext).then(
            (r) => setNote(`Your agent sent the offer${r.seq ? ` (seq ${r.seq})` : ""}.`),
            (error) => setNote(explain(error)),
          )
        }
      />
      {note && (
        <p className="small" role="status">
          {note}
        </p>
      )}
      <VaultForm schema={schema} />
    </div>
  );
}
