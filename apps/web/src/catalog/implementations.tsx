// SPDX-License-Identifier: Apache-2.0
// Helpers every family's implementations share. The implementations live in ./families.
import type { ReactComponentImplementation } from "@a2ui/react/v0_9";
import type { ComponentContext } from "@a2ui/web_core/v0_9";

/** Named events go back to the host as data; the catalog never carries code. */
export function emit(context: ComponentContext, name: string, data: Record<string, unknown> = {}) {
  void context.dispatchAction({ event: { name, context: data } });
}

/** Components outside any family module: none, every catalog component has its family. */
export const implementations: ReactComponentImplementation[] = [];
