// SPDX-License-Identifier: Apache-2.0
import { Catalog } from "@a2ui/web_core/v0_9";
import { implementations } from "./implementations";

export const CATALOG_ID = "coalitionkit/v0_9";

/** The closed catalog this renderer can draw. Anything else is refused and the fixed view shows. */
export const coalitionCatalog = new Catalog(CATALOG_ID, "v0.9", implementations);

export const IMPLEMENTED = implementations.map((i) => i.name);
