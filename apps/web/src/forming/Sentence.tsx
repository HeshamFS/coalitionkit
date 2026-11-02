// SPDX-License-Identifier: Apache-2.0
// The sentence as the headline. A word that produced a card can be pointed at, and the card lights.

const LEADING = /^[.,;:!?]+/;

/** The goal cut into plain stretches and the words the cards came from, in reading order. */
export function pieces(goal: string, words: string[]): { text: string; word: boolean }[] {
  const found = [...new Set(words)]
    .map((w) => ({ w, at: goal.indexOf(w) }))
    .filter((f) => f.w && f.at >= 0)
    .sort((a, b) => a.at - b.at || b.w.length - a.w.length);
  const out: { text: string; word: boolean }[] = [];
  let at = 0;
  for (const f of found) {
    if (f.at < at) continue;
    if (f.at > at) out.push({ text: goal.slice(at, f.at), word: false });
    out.push({ text: f.w, word: true });
    at = f.at + f.w.length;
  }
  if (at < goal.length) out.push({ text: goal.slice(at), word: false });
  return out;
}

export function Sentence({
  goal,
  words,
  hot,
  onHot,
}: {
  goal: string;
  words: string[];
  hot: string | null;
  onHot: (word: string | null) => void;
}) {
  return (
    <>
      {pieces(goal, words).map((p, i, all) => {
        if (!p.word) {
          // A stop or comma right after a word stays with that word, so a line never starts on one.
          const before = all[i - 1]?.word;
          // biome-ignore lint/suspicious/noArrayIndexKey: pieces are positional
          return <span key={i}>{before ? p.text.replace(LEADING, "") : p.text}</span>;
        }
        const tail = all[i + 1];
        const stop = tail && !tail.word ? (LEADING.exec(tail.text)?.[0] ?? "") : "";
        return (
          // biome-ignore lint/suspicious/noArrayIndexKey: pieces are positional
          <span key={i} className="fm-keep">
            <button
              type="button"
              className="fm-word"
              data-hot={hot === p.text}
              onMouseEnter={() => onHot(p.text)}
              onMouseLeave={() => onHot(null)}
              onFocus={() => onHot(p.text)}
              onBlur={() => onHot(null)}
            >
              {p.text}
            </button>
            {stop}
          </span>
        );
      })}
    </>
  );
}
