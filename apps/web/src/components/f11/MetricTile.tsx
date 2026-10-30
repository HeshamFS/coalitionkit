// SPDX-License-Identifier: Apache-2.0
import type { Props, Send } from "../f08/shared";
import "../../styles/f11.css";

import { Metric } from "./controls";
export function MetricTile({ p }: { p: Props; send: Send }) {
  return <Metric p={p} />;
}
