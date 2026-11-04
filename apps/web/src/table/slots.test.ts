// SPDX-License-Identifier: Apache-2.0
import { expect, it } from "vitest";
import { localTimes, slotLabel } from "./slots";

it("reads a host time stamp in a result card in the viewer's own time", () => {
  const stamp = "2026-11-07T11:00:00+00:00";
  const [create, update] = localTimes([
    { createSurface: { surfaceId: "r" } },
    {
      updateComponents: {
        surfaceId: "r",
        components: [
          {
            id: "c",
            component: "Card",
            fields: [
              { label: "Start", value: stamp },
              { label: "Where", value: "To be confirmed" },
            ],
          },
          { id: "t", component: "Text", text: stamp },
        ],
      },
    },
  ]) as Record<string, { components: { fields?: { value: string }[]; text?: string }[] }>[];
  expect(create).toEqual({ createSurface: { surfaceId: "r" } });
  const [card, text] = update?.updateComponents?.components ?? [];
  expect(card?.fields?.[0]?.value).toBe(slotLabel({ id: "", label: stamp, start: stamp }));
  expect(card?.fields?.[0]?.value).not.toContain("T11:00");
  expect(card?.fields?.[1]?.value).toBe("To be confirmed");
  expect(text?.text).toBe(stamp);
});
