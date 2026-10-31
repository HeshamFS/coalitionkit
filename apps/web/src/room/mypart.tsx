// SPDX-License-Identifier: Apache-2.0
// "My part": the Room board. The one answer, the ask, the timeline, what others know about you.
import type { ReactNode } from "react";
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import { deriveParticipants, requestLabel } from "../feed/derive";
import { Germ } from "./germ";
import { Empty, Privacy, Schedule, SeatAvatar } from "./parts";

/** The ask in the Needs-you tone. Approve opens the consent flow; it never commits on its own. */
export function AskCard({
  state,
  request,
  more,
  onApprove,
  onSeePlans,
}: {
  state: ViewerState | null;
  request: OpenRequest;
  more: number;
  onApprove: (id: string) => void;
  onSeePlans: () => void;
}) {
  const choice = request.kind === "tension_option";
  return (
    <article className="room-ask" aria-label="Your agent asks">
      <b className="room-ask-title">Your agent asks before it commits you</b>
      <p>{requestLabel(state, request)}</p>
      <div className="room-ask-actions">
        <button type="button" className="btn btn-primary" onClick={() => onApprove(request.id)}>
          {choice ? "Review choices" : "Approve"}
        </button>
        <button type="button" className="btn" onClick={onSeePlans}>
          See other plans
        </button>
      </div>
      <span className="room-ask-foot">
        signed with your key{more > 0 ? ` · ${more} more waiting` : ""}
      </span>
    </article>
  );
}

export function MyPart({
  state,
  ready,
  requests,
  consent,
  onApprove,
  onSeePlans,
}: {
  state: ViewerState | null;
  ready: boolean;
  requests: OpenRequest[];
  /** The trusted consent flow, shown in place of the ask once Approve was pressed. */
  consent: ReactNode;
  onApprove: (id: string) => void;
  onSeePlans: () => void;
}) {
  const people = deriveParticipants(state);
  const own = people.find((p) => p.id === state?.viewer);
  const others = Math.max(people.length - 1, 0);
  const first = requests[0];
  return (
    <div className="room-mypart">
      <Germ index={0} ready={ready} label="YourPartCard">
        {own ? (
          <article className="room-hero" aria-label="Your part">
            <span className="room-hero-eyebrow">Your part</span>
            {own.item ? (
              <p className="room-hero-answer">{own.item}</p>
            ) : (
              <p className="room-hero-answer room-quiet">Nothing assigned to you yet</p>
            )}
            {own.detail && <p className="room-hero-detail">{own.detail}</p>}
            <div className="room-hero-people">
              {people.slice(0, 4).map((p) => (
                <SeatAvatar key={p.id} seat={p.seat} label={p.label} />
              ))}
              <span>
                {others
                  ? `you and ${others} ${others === 1 ? "other" : "others"}`
                  : "just you for now"}
              </span>
            </div>
          </article>
        ) : (
          <Empty
            title="Your part is not in this projection yet."
            body="It appears here as soon as the coalition assigns it to you."
          />
        )}
      </Germ>
      {consent
        ? consent
        : first && (
            <Germ index={1} ready={ready} label="AskCard">
              <AskCard
                state={state}
                request={first}
                more={requests.length - 1}
                onApprove={onApprove}
                onSeePlans={onSeePlans}
              />
            </Germ>
          )}
      <Schedule state={state} ready={ready} index={2} />
      <Privacy state={state} ready={ready} index={3} own />
    </div>
  );
}
