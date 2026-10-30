// SPDX-License-Identifier: Apache-2.0
import { Catalog } from "@a2ui/web_core/v0_9";
import { implementations as f01 } from "./families/f01";
import { implementations as f02 } from "./families/f02";
import { implementations as f03 } from "./families/f03";
import { implementations as f04 } from "./families/f04";
import { implementations as f05 } from "./families/f05";
import { implementations as f06 } from "./families/f06";
import { implementations as f07 } from "./families/f07";
import { implementations as f08 } from "./families/f08";
import { implementations as f09 } from "./families/f09";
import { implementations as f10 } from "./families/f10";
import { implementations as f11 } from "./families/f11";
import { implementations as first } from "./implementations";

export const CATALOG_ID = "coalitionkit/v0_9";

/** Every implemented component: the first batch, then one module per catalog family. */
export const implementations = [
  ...first,
  ...f01,
  ...f02,
  ...f03,
  ...f04,
  ...f05,
  ...f06,
  ...f07,
  ...f08,
  ...f09,
  ...f10,
  ...f11,
];

/** The closed catalog this renderer can draw. Anything else is refused and the fixed view shows. */
export const coalitionCatalog = new Catalog(CATALOG_ID, "v0.9", implementations);

export const IMPLEMENTED = implementations.map((i) => i.name);
