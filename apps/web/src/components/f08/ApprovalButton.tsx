// SPDX-License-Identifier: Apache-2.0
import type { Props, Send } from "./shared";
import "../../styles/f08.css";

import { Approval } from "./controls";
export function ApprovalButton({ p, send }: { p: Props; send: Send }) {
  return <Approval p={p} send={send} />;
}
