// SPDX-License-Identifier: Apache-2.0
import type { Props, Send } from "./shared";
import "../../styles/f08.css";

import { ConsentView } from "./controls";
export function ConsentCard({ p, send }: { p: Props; send: Send }) {
  return <ConsentView p={p} send={send} />;
}
