// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";
import { One } from "../../gallery/Drawn";
import type { Props } from "./shared";

const bound = (value: number) => ({ value, event_ref: "example" });
function Control({ name, value, ...props }: Props & { name: string; value: unknown }) {
  return <One component={name} props={{ ...props, value: { path: "/value" } }} data={{ value }} />;
}
export function InputPanels({ index }: { index: number }) {
  return demos[index]?.() ?? null;
}

const demos: Record<number, () => ReactNode> = {
  4: () => (
    <>
      <Control
        name="TextField"
        label="Goal"
        value=""
        placeholder="What should this coalition get done?"
        help="empty, with placeholder"
      />
      <Control
        name="TextField"
        label="Goal"
        value="Get the three of us to Place 1 tonight"
        help="focus, typing"
      />
      <One
        component="TextField"
        props={{ label: "Complete by", value: { path: "/value" }, error: { path: "/error" } }}
        data={{
          value: "tomorow 09:00",
          error: 'Couldn\'t read the date. Try "tomorrow 09:00".',
        }}
      />
      <Control
        name="TextField"
        label="Record reference"
        value=""
        readOnly
        private
        help="read only, private"
      />
    </>
  ),
  5: () => (
    <>
      <Control
        name="TextArea"
        label="Note for the other agents"
        value="I can share a resource for the task but I need to be back at Place 1 by 06:30. Ask @Member B about the resource transfer."
        maxLength={bound(500)}
        decorations={[
          { text: "06:30", kind: "bold" },
          { text: "@Member B", kind: "mention" },
        ]}
      />
      <div className="row">
        <One component="Badge" props={{ kind: "vault", label: "Only you and the host" }} />
        <span className="small">The steward checks this before it is shared</span>
      </div>
    </>
  ),
  6: () => (
    <>
      <Control
        name="NumberField"
        label="Units you can offer"
        value={2}
        min={bound(0)}
        max={bound(10)}
        step={bound(1)}
      />
      <Control
        name="NumberField"
        label="Most you'll pay for the resource"
        value={140}
        currency="€"
        unit="per unit"
        help={'Only "yes or no" leaves your vault, never the number'}
      />
      <Control name="NumberField" label="Resource hold time" value={45} unit="min at 1 150 units" />
    </>
  ),
  7: () => (
    <One
      component="SearchField"
      props={{
        query: { path: "/query" },
        groups: [
          {
            label: "Offers",
            items: [
              {
                id: "o1",
                label: "Resource near place 1 · 3 units",
                icon: "resource",
                hint: "Offer",
              },
              {
                id: "o2",
                label: "Resource near place 2 · available",
                icon: "resource",
                hint: "Offer",
              },
            ],
          },
          {
            label: "Needs",
            items: [{ id: "n1", label: "A unit near place 1, before 01:00", icon: "clock" }],
          },
        ],
      }}
      data={{ query: "resource near" }}
    />
  ),
  8: () => (
    <>
      {["all", "two"].map((value) => (
        <div className="field" key={value}>
          <span className="f01-choice-label">Who decides</span>
          <Control
            name="ChoicePicker"
            value={value}
            display="menu"
            options={[
              { id: "all", label: "Every member", hint: "unanimous" },
              { id: "two", label: "Two of three" },
              { id: "one", label: "The organizer only" },
              { id: "weighted", label: "Weighted by share", hint: "v0.2", disabled: true },
            ]}
          />
        </div>
      ))}
    </>
  ),
  9: () => (
    <div className="field">
      <span className="f01-choice-label">What can you offer</span>
      <Control
        name="ChoicePicker"
        value={["a", "b"]}
        multiple
        options={[
          { id: "a", label: "Unit share" },
          { id: "b", label: "Power pack" },
          { id: "c", label: "Resource pass" },
          { id: "d", label: "Spare resource" },
        ]}
      />
    </div>
  ),
  10: () => (
    <>
      <Control
        name="CheckBox"
        label="Share my available time"
        value={true}
        description="Others see the hour, not the task"
      />
      <Control
        name="CheckBox"
        label="Share my documents"
        value="mixed"
        description="2 of 4 selected"
      />
      <Control name="CheckBox" label="Share my contact details" value={false} />
      <One component="Divider" props={{}} />
      <Control
        name="RadioGroup"
        value="all"
        options={[
          { id: "all", label: "Anyone in the coalition" },
          { id: "task", label: "Only people on my task" },
          { id: "public", label: "Public", disabled: true, hint: "blocked by the charter" },
        ]}
      />
    </>
  ),
  11: () => (
    <>
      <Control
        name="Switch"
        label="Let my agent answer yes or no"
        value={true}
        description="without asking me each time"
      />
      <One component="Divider" props={{}} />
      <Control
        name="Switch"
        label="Notify me about changes"
        value={true}
        description="only when I need to decide"
      />
      <One component="Divider" props={{}} />
      <Control
        name="Switch"
        label="Voice on the glasses"
        value={false}
        description="turned off by you"
      />
    </>
  ),
  12: () => (
    <>
      <div className="field">
        <span className="lbl f01-slider-label">At most</span>
        <Control name="Slider" value={12} min={bound(0)} max={bound(30)} unit="min" />
      </div>
      <div className="field">
        <span className="lbl f01-slider-label">Available range</span>
        <Control
          name="Slider"
          value={[1290, 1380]}
          min={bound(1240)}
          max={bound(1440)}
          format="time"
        />
      </div>
      <div className="field">
        <span className="lbl f01-slider-label">Fair share</span>
        <Control
          name="Slider"
          value={52}
          min={bound(0)}
          max={bound(100)}
          unit="%"
          marks={[{ at: bound(30), label: "floor" }]}
          valueLabel="your floor 30 %"
        />
      </div>
    </>
  ),
  13: () => (
    <>
      <Control
        name="SegmentedControl"
        value="Plan"
        options={["Plan", "People", "Log"].map((label) => ({ id: label, label }))}
      />
      <Control
        name="Tabs"
        value="needs"
        options={[
          { id: "needs", label: "Needs", count: bound(3) },
          { id: "offers", label: "Offers", count: bound(7) },
          { id: "tasks", label: "Tasks" },
          { id: "done", label: "Done" },
        ]}
      />
      <Control
        name="ChoicePicker"
        value="All"
        display="chips"
        options={["All", "Needs you", "Changed", "Private"].map((label) => ({ id: label, label }))}
      />
    </>
  ),
};
