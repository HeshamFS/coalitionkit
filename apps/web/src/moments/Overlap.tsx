// SPDX-License-Identifier: Apache-2.0
import "./overlap.css";

/** One blinded point seen crossing the host. `fingerprint` is a short hex digest, never the blob. */
export type Crossing = { seq: number; round: string; dir: "out" | "in"; fingerprint: string };

export type OverlapProps = {
  crossings: Crossing[];
  /** Only the viewer's own entries. Absent: the vault is held by the viewer's agent. */
  vault?: string[];
  /** A count for the other side, if the host may state one. Never their entries. */
  theirCount?: number;
  /** Arrives only on the requester's own channel. Never derived from the log. */
  result?: { shared: string; keptPrivate: number };
};

export function Overlap({ crossings, vault, theirCount, result }: OverlapProps) {
  const lit = (entry: string) => (result ? entry === result.shared : false);
  return (
    <section className="mo-overlap" aria-label="Overlap">
      <p className="mo-o-eyebrow">Private set intersection</p>
      <h3>
        They find what they share. <em>Nothing else crosses.</em>
      </h3>
      <div className="mo-o-stage">
        <div className="mo-o-vault" data-side="mine">
          <span className="mo-o-cap">Your vault · on your device</span>
          {vault ? (
            vault.map((v) => (
              <span key={v} className="mo-o-entry" data-lit={lit(v)}>
                {v}
              </span>
            ))
          ) : (
            <span className="mo-o-note">Your vault is held by your agent</span>
          )}
          <span className="mo-o-note">never leaves this circle</span>
        </div>
        <div className="mo-o-host">
          <span className="mo-o-cap">The host only relays blinded points</span>
          <ol className="mo-o-lane" aria-label="Blinded points crossing the host">
            {crossings.length === 0 ? <li className="mo-o-note">No exchange yet</li> : null}
            {crossings.map((c, i) => (
              <li key={c.seq} className="mo-o-row" data-dir={c.dir}>
                <span
                  className="mo-o-point"
                  data-dir={c.dir}
                  style={{ animationDelay: `${i * 600}ms` }}
                  title={`${c.round} · seq ${c.seq}`}
                >
                  {c.fingerprint}
                </span>
              </li>
            ))}
          </ol>
        </div>
        <div className="mo-o-vault" data-side="theirs">
          <span className="mo-o-cap">Their vault · hosted for them</span>
          {typeof theirCount === "number" ? (
            <span className="mo-o-entry">{theirCount} entries</span>
          ) : null}
          <span className="mo-o-note">never leaves their circle</span>
        </div>
      </div>
      <div className="mo-o-result" role="status">
        <span className="mo-o-dot" aria-hidden="true" />
        {result ? (
          <>
            <span className="mo-o-strong">Shared: {result.shared}</span>
            <span className="mo-o-soft">your other {result.keptPrivate} stayed private</span>
          </>
        ) : (
          <span className="mo-o-soft">
            Matching… the result appears only on each member's own screen
          </span>
        )}
      </div>
      <p className="mo-o-mono">ECDH-PSI over ristretto255 · coalition.match</p>
    </section>
  );
}
