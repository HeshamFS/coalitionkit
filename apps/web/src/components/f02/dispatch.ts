// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { emit } from "../../catalog/implementations";

const reviewEvents = new Set([
  "charter.accept",
  "consent.open",
  "sign.confirm",
  "decide.change",
  "elicitation.accept",
  "elicitation.decline",
]);

/** Catalog intent is observable, but only the trusted request UI may construct an answer. */
export function dispatch(
  context: ComponentContext,
  name: string,
  data: Record<string, unknown> = {},
) {
  emit(context, name, data);
  if (reviewEvents.has(name) && data.subject) emit(context, "open", { subject: data.subject });
}
