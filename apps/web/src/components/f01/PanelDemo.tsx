// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";
import { Drawn, One } from "../../gallery/Drawn";
import { CommandPanel, ListPanel, TablePanel } from "./DataPanels";
import { examples } from "./examples";
import { InputPanels } from "./InputPanels";
import { Files, Images, VideoPanel, VoiceNote } from "./MediaPanels";
import { OverlayPanels } from "./OverlayPanels";
import { SlotsPanel } from "./SlotsPanel";
import type { Props } from "./shared";
import { TooltipPanel } from "./TooltipPanel";

export function Sample({ name, props, data }: { name: string; props?: Props; data?: Props }) {
  const sample = examples(name)[0];
  return (
    <Drawn
      label={name}
      data={data ?? sample?.data}
      components={[
        { id: "root", component: name, ...sample?.props, ...props },
        { id: "body", component: "Text", text: "Review the details with your coalition." },
        {
          id: "action1",
          component: "Button",
          label: "Continue",
          variant: "primary",
          action: { name: "continue" },
        },
        { id: "action2", component: "Button", label: "Cancel", action: { name: "cancel" } },
      ]}
    />
  );
}
const bound = (value: number) => ({ value, event_ref: "example" });
const B = ({ label, ...props }: Props & { label: string }) => (
  <One component="Button" props={{ label, ...props }} />
);
const groups: Record<number, string[]> = {
  4: ["TextField"],
  5: ["TextArea"],
  6: ["NumberField"],
  7: ["SearchField"],
  8: ["ChoicePicker"],
  9: ["ChoicePicker"],
  10: ["CheckBox", "RadioGroup"],
  11: ["Switch"],
  12: ["Slider"],
  13: ["SegmentedControl", "Tabs"],
  14: ["FilterBar"],
  15: ["DateTimeInput"],
  16: ["SlotPicker"],
  17: ["Deadline", "TimeZone"],
  18: ["Tooltip"],
  19: ["Popover"],
  20: ["Menu"],
  21: ["Modal"],
  22: ["Sheet"],
  23: ["Drawer"],
  24: ["Toast"],
  26: ["Progress", "Meter"],
  29: ["ErrorState"],
  30: ["CommandPalette"],
  31: ["Table"],
  32: ["List"],
  35: ["Chip", "Link", "Divider"],
  36: ["Image"],
  37: ["Video"],
  38: ["AudioPlayer"],
  39: ["FileDrop"],
};
export function PanelDemo({ index }: { index: number }) {
  if (index === 14)
    return (
      <Sample
        name="FilterBar"
        props={{
          placeholder: "Filter offers",
          resultLabel: "12 offers · 4 match your needs",
          options: [
            {
              field: "Owner",
              options: [
                { value: "Member A", label: "Member A" },
                { value: "Member B", label: "Member B" },
              ],
            },
            { field: "Task", options: [{ value: "t1", label: "Task 1" }] },
            { field: "Scope", options: [{ value: "coalition", label: "Coalition" }] },
          ],
        }}
      />
    );
  if (index === 15)
    return (
      <One
        component="DateTimeInput"
        props={{
          range: true,
          mode: "date",
          value: { path: "/range" },
          busy: ["2026-11-10", "2026-11-11"],
        }}
        data={{ range: ["2026-11-12", "2026-11-14"] }}
      />
    );
  if (index === 18) return <TooltipPanel />;
  if (index === 16) return <SlotsPanel />;
  if (index === 26)
    return (
      <>
        <Sample name="Progress" />
        <One
          component="Progress"
          props={{ label: "Waiting for answers", value: bound(2), max: bound(3), steps: bound(3) }}
        />
        <One
          component="Progress"
          props={{ label: "Workflow", value: bound(2), stepLabels: ["Join", "Offer", "Decide"] }}
        />
        <Sample
          name="Meter"
          props={{ label: "Resource at 64 % of hold", caption: "29 of 45 min" }}
        />
      </>
    );
  if (index === 17)
    return (
      <>
        <One
          component="Deadline"
          props={{
            label: "Decide by 22:40",
            deadline: "2026-10-30T22:40:00Z",
            startedAt: "2026-10-30T21:51:35Z",
            consequence: "After this the plan goes back to planning",
          }}
        />
        <One
          component="TimeZone"
          props={{
            value: "Europe/Lisbon",
            label: "Place 1 · WET, UTC+0",
            at: "2026-11-12T22:40:00Z",
            others: [
              { participant: "Member B", tz: "Europe/Berlin" },
              { participant: "Member C", tz: "Asia/Tokyo" },
            ],
          }}
        />
      </>
    );
  if (index === 29) return <Sample name="ErrorState" props={{ missedEvents: bound(3) }} />;
  if (index === 30) return <CommandPanel />;
  if (index === 31) return <TablePanel />;
  if (index === 32) return <ListPanel />;
  if (index === 36) return <Images />;
  if (index === 37) return <VideoPanel />;
  if (index === 38) return <VoiceNote />;
  if (index === 39) return <Files />;
  if (index >= 4 && index <= 13) return <InputPanels index={index} />;
  if (index >= 19 && index <= 24) return <OverlayPanels index={index} />;
  return demos[index]?.() ?? (groups[index] ?? []).map((name) => <Sample key={name} name={name} />);
}

const demos: Record<number, () => ReactNode> = {
  0: () => (
    <>
      <div className="row wrap">
        <B label="Accept plan" variant="primary" />
        <B label="Ask a question" />
      </div>
      <div className="row wrap">
        <B label="Sign as owner" variant="ink" />
        <B label="Suggest a change" tone="soft" />
      </div>
      <div className="row wrap">
        <B label="Not now" variant="ghost" />
        <B label="Leave coalition" tone="danger" />
        <B label="Revoke" tone="danger-fill" />
      </div>
    </>
  ),
  1: () => (
    <>
      <div className="g3" style={{ gap: 8 }}>
        {["default", "hover", "pressed", "focus", "busy", "disabled"].map((state) => (
          <div className={`col f01-demo-${state}`} key={state}>
            <B
              label={state === "busy" ? "Sending" : "Accept"}
              variant="primary"
              busy={state === "busy"}
              disabled={state === "disabled"}
            />
            <span className="st">{state}</span>
          </div>
        ))}
      </div>
      <div className="row">
        <B label="Accept" disabled />
        <span className="small">Waiting for 2 deciders before this unlocks</span>
      </div>
    </>
  ),
  2: () => (
    <>
      <div className="row wrap">
        <B label="Small" size="sm" />
        <B label="Default" />
        <B label="Large 44" size="lg" variant="primary" />
      </div>
      <div className="row wrap">
        <B label="Add an offer" icon="plus" />
        <B label="Continue" trailingIcon="arrow" />
      </div>
      <Drawn
        components={[
          { id: "root", component: "Row", children: ["more", "copy", "close", "tip"] },
          { id: "more", component: "IconButton", ariaLabel: "More actions", icon: "more" },
          { id: "copy", component: "IconButton", ariaLabel: "Copy the invite link", icon: "copy" },
          { id: "close", component: "IconButton", ariaLabel: "Close", icon: "x" },
          { id: "tip", component: "Tooltip", target: "copy", tip: "Copy the invite link" },
        ]}
      />
    </>
  ),
  3: () => (
    <>
      <Drawn
        components={[
          { id: "root", component: "ButtonGroup", children: ["day", "week", "month"] },
          ...["day", "week", "month"].map((id) => ({
            id,
            component: "Button",
            ...(id === "week" ? { tone: "soft" } : {}),
            label: id[0]?.toUpperCase() + id.slice(1),
          })),
        ]}
      />
      <Sample
        name="SplitButton"
        props={{
          primary: "a",
          items: [
            { label: "Propose plan A", value: "a", hint: "fastest" },
            { label: "Propose A and B together", value: "ab" },
            { label: "Propose B", value: "b", hint: "cheapest" },
            { label: "Propose C", value: "c", hint: "needs Member C", disabled: true },
          ],
        }}
      />
    </>
  ),
  25: () => (
    <>
      {[
        ["info", "The charter changed.", "Read revision 3 before you accept anything new."],
        ["ask", "Two plans tie.", "The organizer breaks the tie by 22:40."],
        ["blocked", "The steward blocked a message", "that named your resource. Nothing was sent."],
        ["agreed", "Everyone agreed.", "The plan is signed."],
      ].map(([tone, title, body]) => (
        <One key={tone} component="Banner" props={{ tone, title, body }} />
      ))}
    </>
  ),
  27: () => (
    <>
      <One component="Skeleton" props={{ shape: "card" }} />
      <Sample name="Spinner" props={{ label: "Your agent is reading the offers…" }} />
    </>
  ),
  28: () => <Sample name="EmptyState" />,
  33: () => (
    <>
      <Sample name="KeyValue" />
      <div className="row wrap">
        {["agreed", "needs", "changed", "private", "blocked"].map((kind) => (
          <One
            key={kind}
            component="Tag"
            props={{
              kind,
              label: kind === "needs" ? "Needs you" : kind[0]?.toUpperCase() + kind.slice(1),
            }}
          />
        ))}
      </div>
      <div className="row wrap">
        {[
          ["measured", "Measured"],
          ["signed", "Signed"],
          ["vault", "Vault answer"],
          ["model", "Model output"],
          ["estimate", "Estimate"],
        ].map(([kind, label]) => (
          <One key={kind} component="Badge" props={{ kind, label }} />
        ))}
      </div>
    </>
  ),
  35: () => (
    <>
      <div className="row wrap">
        <One component="Chip" props={{ label: "Task" }} />
        <One component="Chip" props={{ label: "Place ✓", selected: true }} />
        <One component="Chip" props={{ label: "Set B", seat: "2" }} />
        <One component="Chip" props={{ label: "+ Add a need", dashed: true }} />
        <One component="Chip" props={{ label: "Blocked by charter", disabled: true }} />
      </div>
      <div className="row wrap small">
        <One
          component="Link"
          props={{ text: "Read the charter", href: "https://example.invalid/charter" }}
        />
        <span>·</span>
        <One component="Link" props={{ text: "log #42", href: "https://example.invalid/log/42" }} />
        <span>·</span>
        <span>
          Press <kbd className="kbd">⌘</kbd> <kbd className="kbd">K</kbd> to jump anywhere
        </span>
      </div>
      <One component="Divider" props={{ label: "earlier today" }} />
    </>
  ),
  34: () => (
    <>
      <div className="row">
        {["xs", "sm", "lg", "xl", "lg"].map((size, i) => (
          <One
            key={"ABCDE"[i]}
            component="Avatar"
            props={{
              size,
              seat: i === 4 ? "host" : String(i + 1),
              label: i === 4 ? "Host" : `Member ${"ABCD"[i]}`,
            }}
          />
        ))}
      </div>
      <div className="row" style={{ gap: 14 }}>
        {["live", "away", "off", undefined].map((presence, i) => (
          <One
            key={presence ?? "ring"}
            component="Avatar"
            props={{
              size: "lg",
              seat: String(i + 1),
              label: `Member ${"ABCD"[i]}`,
              presence,
              ring: i === 3,
            }}
          />
        ))}
      </div>
      <div className="row">
        <Sample name="AvatarStack" props={{ max: bound(3) }} />
        <span className="small">5 agents are reading</span>
      </div>
    </>
  ),
};
