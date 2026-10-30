// SPDX-License-Identifier: Apache-2.0
import type { FC } from "react";
import { Sheet01 } from "./Sheet01";
import { Sheet02 } from "./Sheet02";
import { Sheet03 } from "./Sheet03";
import { Sheet04 } from "./Sheet04";
import { Sheet05 } from "./Sheet05";
import { Sheet06 } from "./Sheet06";
import { Sheet07 } from "./Sheet07";
import { Sheet08 } from "./Sheet08";
import { Sheet09 } from "./Sheet09";
import { Sheet10 } from "./Sheet10";
import { Sheet11 } from "./Sheet11";

/** One gallery page per design sheet, keyed by family number: /gallery/01 to /gallery/11. */
export const SHEETS: Record<string, FC> = {
  "01": Sheet01,
  "02": Sheet02,
  "03": Sheet03,
  "04": Sheet04,
  "05": Sheet05,
  "06": Sheet06,
  "07": Sheet07,
  "08": Sheet08,
  "09": Sheet09,
  "10": Sheet10,
  "11": Sheet11,
};
