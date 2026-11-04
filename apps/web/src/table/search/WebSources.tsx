// SPDX-License-Identifier: Apache-2.0
// The web pages a result came from, and what the agents searched to find them. Links open in a
// new tab with no referrer; the queries shown are the screened words that left the host.
import type { RoomSearch, WebLink } from "./links";
import "./web.css";

const host = (url: string) => {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
};

function searchLine(s: RoomSearch): string {
  if (s.stopped) return `A search was refused: ${s.stopped}.`;
  const took = s.ms === null ? "" : `, ${(s.ms / 1000).toFixed(1)} s`;
  const words = s.ran.length > 0 ? s.ran.join('", "') : s.query;
  return `Searched "${words}" (${s.provider}): ${s.count} found${took}.`;
}

export function WebSources({
  links,
  searches = [],
  compact = false,
}: {
  links: WebLink[];
  searches?: RoomSearch[];
  compact?: boolean;
}) {
  if (links.length === 0 && (compact || searches.length === 0)) return null;
  return (
    <section className="tb-web" aria-label="Sources on the web">
      <h4>{compact ? "Found on the web" : "Sources on the web"}</h4>
      {links.length > 0 && (
        <ol className="tb-web-links">
          {links.map((l) => (
            <li key={l.url}>
              <a href={l.url} target="_blank" rel="noopener noreferrer">
                {l.title}
              </a>
              {l.title !== host(l.url) && <span className="tb-quiet"> {host(l.url)}</span>}
            </li>
          ))}
        </ol>
      )}
      {!compact &&
        searches.map((s) => (
          <p key={s.id} className="tb-quiet tb-web-query">
            {searchLine(s)}
          </p>
        ))}
    </section>
  );
}
