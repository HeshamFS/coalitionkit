// SPDX-License-Identifier: Apache-2.0
// Every consent on the Table is drawn here, by the existing trusted request and its seal, from the
// host's own request. Nothing composed can reach it; the tree's actions only focus a request.
import type { OpenRequest } from "../feed/agent";
import { humanTime, requestLabel } from "../feed/derive";
import { TrustedRequest } from "../TrustedRequest";
import { useTable } from "./context";
import type { Room } from "./room";

/** The host's plain words for a request, from `mine.asks`, when it sent them. */
export const summaryOf = (room: Room, r: OpenRequest): string | undefined =>
  room.mine.asks?.find((a) => a.id === r.subjectId)?.summary;

/** The host's plain words for a request, when it sent them. */
export function useSummary(request: OpenRequest): string | undefined {
  const { room } = useTable();
  return summaryOf(room, request);
}

export function AskCard({ request }: { request: OpenRequest }) {
  const { state, answer, setFocus } = useTable();
  const summary = useSummary(request);
  return (
    <TrustedRequest
      key={`${request.id}:${request.revision}`}
      request={{ ...request, message: requestLabel(state, request) }}
      state={state}
      onAnswer={answer}
      onSeePlans={() => setFocus(null)}
      summary={summary}
      compact
    />
  );
}

/** The open request in focus, or the list of what waits for a yes (filtered by kind). */
export function Asks({
  kinds,
  title = "Waiting for your yes",
}: {
  kinds?: string[];
  title?: string;
}) {
  const { asks, requests, focus, setFocus, state, room } = useTable();
  const open = requests.find((r) => r.id === focus && (!kinds || kinds.includes(r.kind)));
  if (open) return <AskCard request={open} />;
  const shown = asks.filter((r) => !kinds || kinds.includes(r.kind));
  if (shown.length === 0) return null;
  return (
    <section className="tb-asks" aria-label={title}>
      <span className="tb-tag">{title}</span>
      <ul>
        {shown.map((r) => (
          <li key={r.id}>
            <button type="button" className="btn tb-ask" onClick={() => setFocus(r.id)}>
              <span>{summaryOf(room, r) ?? requestLabel(state, r)}</span>
              {r.expiresAt && <small>decide by {humanTime(r.expiresAt)}</small>}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
