// SPDX-License-Identifier: Apache-2.0
// One ending for everyone: the Table with its ring folded into the mark, the results kept in this
// tab, and what was erased and learned on your side. It is what the person who pressed End sees
// (after the host has dissolved the room) and what anyone else sees when their session closes.
import { useCallback, useEffect, useRef, useState } from "react";
import { clearToken } from "../feed/config";
import { dissolveCoalition, HostError } from "../genesis/api";
import { clearOwner } from "../genesis/owner";
import type { CleanupReport, DissolveEvent } from "../moments/Dissolve";
import { EndedView } from "../room/endCoalition";
import { clearEnded, type EndRun, readEnded } from "../room/ended";
import { usePhoneRoom } from "../room/media";
import type { RoomIo } from "./api";
import { KeptResults, readSavedRoom } from "./keep";
import { TableView } from "./TableView";

const no = async () => ({ ok: false as const, status: 0, error: "ended", detail: "", auth: false });
const closed: RoomIo = { begin: no, brief: no, say: no, done: no, viewAs: no };

export function EndedTable({
  run,
  event,
  onLeave,
}: {
  run?: EndRun;
  event?: DissolveEvent | null;
  onLeave: () => void;
}) {
  const [saved] = useState(readSavedRoom);
  const phone = usePhoneRoom();
  const [report, setReport] = useState<CleanupReport>();
  const [refused, setRefused] = useState("");
  const asked = useRef(false);
  const ask = useCallback((r: EndRun) => {
    setReport(undefined);
    setRefused("");
    dissolveCoalition(r.token, r.reason).then(setReport, (error: unknown) =>
      setRefused(
        error instanceof HostError
          ? `The host refused (${error.status}). Nothing was ended.`
          : "No answer came back from the host, so it is not known whether the room ended. Try again to find out: asking twice is safe.",
      ),
    );
  }, []);
  useEffect(() => {
    // The plain closing page asks the host itself; only the Table does it here.
    if (!run || !saved || asked.current) return;
    asked.current = true;
    ask(run);
  }, [run, saved, ask]);
  const leave = () => {
    clearToken();
    clearOwner();
    clearEnded();
    onLeave();
  };
  // A room this tab never drew as the Table has nothing to fold: the plain closing page stands.
  if (!saved) {
    return (
      <>
        <EndedView run={run} event={event} onLeave={onLeave} />
        <KeptResults />
      </>
    );
  }
  return (
    <TableView
      room={{ ...saved.room, phase: "ended", lights: "day" }}
      state={saved.state}
      requests={[]}
      focus={null}
      setFocus={() => {}}
      answer={async () => undefined}
      outcome={async () => ({ ok: false, error: "ended", detail: "" })}
      io={closed}
      phone={phone}
      owner={false}
      status="live"
      ending={{
        report,
        event: event ?? readEnded(),
        refused,
        pending: Boolean(run) && !report && !refused,
        onRetry: run ? () => ask(run) : undefined,
        onLeave: leave,
      }}
    />
  );
}
