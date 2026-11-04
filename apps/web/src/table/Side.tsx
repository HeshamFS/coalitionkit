// SPDX-License-Identifier: Apache-2.0
// Your side: one panel by phase, or the other person's screen when you are looking as them.
import type { Plan } from "../components/f06/plans";
import { useTable } from "./context";
import { Devices } from "./mint/Devices";
import { type SideKind, sideFor } from "./phase";
import type { RoomSeat } from "./room";
import { SeeAs } from "./SeeAs";
import { SideBrief } from "./SideBrief";
import { SideEnded, SideLive } from "./SideEnd";
import { SideGather } from "./SideGather";
import { SideCommit, SideDecide, SideWork } from "./SideMid";

const NOTE: Record<SideKind, string> = {
  gather: "Your yes is signed for you by the host, after you say it.",
  brief: "Your answers stay in your vault.",
  work: "Only you get this feed. Others see offers, never its words.",
  decide: "The same plans for everyone. The line marked for you only is yours alone.",
  commit: "Agents never commit anyone. Only your own yes does.",
  live: "Only your tasks. Anything that commits you asks you again.",
  ended: "The feed has closed. What was made stays.",
};

export function Side({
  looking,
  onBack,
  plans,
  selected,
  onPick,
}: {
  looking: RoomSeat | null;
  onBack: () => void;
  plans: Plan[];
  selected: string | null;
  onPick: (id: string) => void;
}) {
  const { room, phone } = useTable();
  const kind = sideFor(room.phase);
  return (
    <aside className="tb-side" aria-label="Your side">
      <div className="tb-sidehead">
        <span>{looking ? "Seen as someone else" : "Your side"}</span>
        <span className="tb-tag">{looking ? "Composed on the host" : "Only you see this"}</span>
      </div>
      {looking ? (
        <SeeAs key={looking.seat} seat={looking} onBack={onBack} />
      ) : (
        <>
          {kind === "gather" && <SideGather />}
          {kind === "brief" && <SideBrief />}
          {kind === "work" && <SideWork />}
          {kind === "decide" && (
            <SideDecide plans={plans} selected={selected} onPick={onPick} phone={phone} />
          )}
          {kind === "commit" && <SideCommit />}
          {kind === "live" && <SideLive />}
          {kind === "ended" && <SideEnded />}
          <Devices />
        </>
      )}
      <div className="tb-composed">
        {looking ? "Only what you both may see is shown." : NOTE[kind]}
      </div>
    </aside>
  );
}
