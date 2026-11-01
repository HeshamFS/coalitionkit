// SPDX-License-Identifier: Apache-2.0
// Words for the core objects. A pack may rename them for its viewers; the screens read every such
// noun through this one place, so a room without a pack reads exactly as the core words.
import { createContext, type ReactNode, useContext, useMemo } from "react";
import type { ViewerState } from "./delta";

export type Word = string | { one: string; other: string };
export type WordFn = (key: string, count?: number) => string;

const CORE: Record<string, readonly [string, string]> = {
  need: ["need", "needs"],
  offer: ["offer", "offers"],
  task: ["task", "tasks"],
  resource: ["resource", "resources"],
  plan: ["plan", "plans"],
  commitment: ["commitment", "commitments"],
  tension: ["tension", "tensions"],
  charter: ["charter", "charters"],
  decision: ["decision", "decisions"],
};

const isPlural = (v: unknown): v is { one: string; other: string } =>
  v !== null &&
  typeof v === "object" &&
  typeof (v as { one?: unknown }).one === "string" &&
  typeof (v as { other?: unknown }).other === "string";

/** The pack words a viewer state carries; anything that is not a string or a plural is ignored. */
export function packWords(state: ViewerState | null): Record<string, Word> {
  const pack = state?.pack;
  const raw =
    pack && typeof pack === "object" ? (pack as { vocabulary?: unknown }).vocabulary : null;
  if (!raw || typeof raw !== "object") return {};
  const words: Record<string, Word> = {};
  for (const [key, value] of Object.entries(raw)) {
    if (typeof value === "string" && value) words[key] = value;
    else if (isPlural(value)) words[key] = value;
  }
  return words;
}

/**
 * The word for a key. One when `count` is 1 or absent, the plural otherwise. A pack word given as
 * one string is used for every count. A key the pack does not rename falls back to the core word,
 * and a key that is no core object (a role id, say) comes back as it was given.
 */
export function makeWord(words: Record<string, Word>): WordFn {
  return (key, count) => {
    const one = count === undefined || count === 1;
    const hit = words[key];
    if (typeof hit === "string") return hit;
    if (hit) return one ? hit.one : hit.other;
    const core = CORE[key];
    return core ? core[one ? 0 : 1] : key;
  };
}

/** For code that holds a viewer state and no React tree. */
export const wordsOf = (state: ViewerState | null): WordFn => makeWord(packWords(state));

/** The same word with a capital first letter, for the start of a label. */
export const capital = (text: string): string => text.charAt(0).toUpperCase() + text.slice(1);

const CoreWords = makeWord({});
const Ctx = createContext<WordFn>(CoreWords);

export function VocabularyProvider({
  state,
  children,
}: {
  state: ViewerState | null;
  children: ReactNode;
}) {
  const words = state?.pack;
  // The pack object only changes when the host sends a new one.
  // biome-ignore lint/correctness/useExhaustiveDependencies: keyed on the pack object on purpose
  const word = useMemo(() => wordsOf(state), [words]);
  return <Ctx.Provider value={word}>{children}</Ctx.Provider>;
}

/** `word(key, count?)` for the room the viewer is in; core words outside a provider. */
export const useVocabulary = (): { word: WordFn } => ({ word: useContext(Ctx) });
