// SPDX-License-Identifier: Apache-2.0
import type { Props, Send } from "./shared";
import "../../styles/f08.css";

import { Disclosure } from "./controls";
export function DisclosureLadder({ p, send }: { p: Props; send: Send }) {
  return <Disclosure p={p} send={send} />;
}
