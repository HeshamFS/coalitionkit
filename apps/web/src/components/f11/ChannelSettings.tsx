// SPDX-License-Identifier: Apache-2.0
import type { Props, Send } from "../f08/shared";
import "../../styles/f11.css";

import { Channels } from "./controls";
export function ChannelSettings({ p, send }: { p: Props; send: Send }) {
  return <Channels p={p} send={send} />;
}
