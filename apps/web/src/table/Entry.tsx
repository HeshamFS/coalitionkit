// SPDX-License-Identifier: Apache-2.0
// One switch: the Table when the host sent `state.room`, the five-tab room when it did not.

import { useFeedSnapshot } from "../feed/useFeed";
import { RoomView } from "../RoomView";
import { readRoom } from "./room";
import { Table } from "./Table";

export function RoomEntry() {
  const feed = useFeedSnapshot();
  return readRoom(feed.state) ? <Table /> : <RoomView />;
}
