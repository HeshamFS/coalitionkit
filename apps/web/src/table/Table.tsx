// SPDX-License-Identifier: Apache-2.0
// The live Table: the real feed, the real requests and the real routes, handed to the same screen
// the gallery shows. It stands in for the five-tab room whenever the host sent `state.room`.
import { useEffect, useMemo } from "react";
import { useAgentSnapshot, useFeedApi, useFeedSnapshot } from "../feed/useFeed";
import { isOwner } from "../genesis/owner";
import { rememberEnded } from "../room/ended";
import { usePhoneRoom } from "../room/media";
import { dissolvedEvent } from "../room/moments";
import { liveIo } from "./api";
import { readRoom } from "./room";
import { TableView } from "./TableView";

export function Table() {
  const feed = useFeedSnapshot();
  const agent = useAgentSnapshot();
  const { answer, agent: store, signOut } = useFeedApi();
  const phone = usePhoneRoom();
  const io = useMemo(() => liveIo(), []);
  const room = readRoom(feed.state);
  const dissolved = dissolvedEvent(feed.state);
  const key = dissolved ? `${dissolved.reason}|${dissolved.skills_written.join(",")}` : "";
  // biome-ignore lint/correctness/useExhaustiveDependencies: the key stands for the event's contents
  useEffect(() => {
    if (dissolved) rememberEnded(dissolved);
  }, [key]);
  if (!room) return null;
  return (
    <TableView
      room={room}
      state={feed.state}
      requests={agent.requests}
      focus={agent.focus}
      setFocus={(id) => store.setFocus(id)}
      answer={answer}
      io={io}
      phone={phone}
      owner={isOwner()}
      status={feed.status}
      refusal={agent.refusal}
      onSignOut={signOut}
    />
  );
}
