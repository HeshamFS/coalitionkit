// SPDX-License-Identifier: Apache-2.0
import { One } from "../../gallery/Drawn";

const days = [
  ["Wed 12", ["09:00", "10:30", "13:00", "15:30"], ["off", "shared", "free", "off"]],
  ["Thu 13", ["09:00", "11:00", "14:00", "16:00"], ["mine", "shared", "off", "free"]],
  ["Fri 14", ["09:00", "11:30", "14:00", "16:30"], ["off", "off", "free", "off"]],
  ["Mon 17", ["09:30", "12:00", "14:30", "17:00"], ["free", "shared", "off", "free"]],
  ["Tue 18", ["08:30", "10:00", "13:00", "15:00"], ["off", "free", "off", "off"]],
] as const;
export function SlotsPanel() {
  return (
    <One
      component="SlotPicker"
      props={{
        days: days.map(([date, times, states]) => ({
          date,
          slots: times.map((time, i) => ({
            start: `2026-11-${date.slice(-2)}T${time}:00Z`,
            state: states[i],
          })),
        })),
        selected: "2026-11-13T09:00:00Z",
        duration: { value: 30, event_ref: "example" },
        source: "psi_match",
      }}
    />
  );
}
