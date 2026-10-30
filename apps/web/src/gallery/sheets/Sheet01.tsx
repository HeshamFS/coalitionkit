// SPDX-License-Identifier: Apache-2.0
import { apis } from "../../catalog/families/f01";
import { examples } from "../../components/f01/examples";
import { metadata } from "../../components/f01/metadata";
import { Cell, Family, State } from "../Cell";
import { Drawn } from "../Drawn";

export { examples } from "../../components/f01/examples";

const sections: [string, string, string[]][] = [
  ["01a", "Buttons and actions", ["Button", "IconButton", "ButtonGroup", "SplitButton"]],
  ["01b", "Text and numbers", ["TextField", "TextArea", "NumberField", "SearchField"]],
  [
    "01c",
    "Choice",
    [
      "ChoicePicker",
      "CheckBox",
      "RadioGroup",
      "Switch",
      "Slider",
      "SegmentedControl",
      "Tabs",
      "FilterBar",
    ],
  ],
  ["01d", "Date and time", ["DateTimeInput", "SlotPicker", "Deadline", "TimeZone"]],
  [
    "01e",
    "Overlays: tooltip, popover, menu, modal, sheet, drawer",
    ["Tooltip", "Popover", "Menu", "Modal", "Sheet", "Drawer", "Toast", "Banner"],
  ],
  [
    "01f",
    "Progress, loading, empty and error",
    ["Progress", "Meter", "Skeleton", "Spinner", "EmptyState", "ErrorState"],
  ],
  [
    "01g",
    "Command palette and data display",
    [
      "CommandPalette",
      "Table",
      "List",
      "KeyValue",
      "Badge",
      "Tag",
      "Avatar",
      "AvatarStack",
      "Chip",
      "Link",
      "Divider",
    ],
  ],
  ["01h", "Media and files", ["Image", "Video", "AudioPlayer", "FileDrop"]],
  [
    "01i",
    "Typography and layout",
    ["Text", "Heading", "RichText", "Icon", "Row", "Column", "Grid", "Card", "Panel"],
  ],
];
export function Sheet01() {
  return (
    <div className="sheet sheet-01" data-testid="sheet-01">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 01 · example data</div>
          <div className="sheet-title">Foundations</div>
        </div>
      </div>
      {sections.map(([n, title, names]) => (
        <Family key={n} n={n} title={title}>
          {names.map((name) => (
            <Cell
              key={name}
              name={name}
              props={Object.keys(apis.find((a) => a.name === name)?.schema.shape ?? {}).join(" · ")}
              doors={metadata[name]?.doors}
              events={metadata[name]?.events.join(" · ") || "display only"}
            >
              {examples(name).map((sample) => (
                <State key={JSON.stringify(sample)} label={sample.label ?? "default"}>
                  <Drawn
                    label={name}
                    data={sample.data}
                    components={[
                      ...(name === "Tooltip"
                        ? [
                            {
                              id: "root",
                              component: "Column",
                              children: ["tooltip-target", "tip"],
                            },
                            {
                              id: "tooltip-target",
                              component: "Button",
                              label: "Audience",
                              variant: "secondary",
                            },
                            { id: "tip", component: "Tooltip", ...sample.props },
                          ]
                        : [{ id: "root", component: name, ...sample.props }]),
                      {
                        id: "body",
                        component: "Text",
                        text: "Review the details with your coalition.",
                      },
                      {
                        id: "action1",
                        component: "Button",
                        label: "Continue",
                        variant: "primary",
                        action: { name: "continue" },
                      },
                      {
                        id: "action2",
                        component: "Button",
                        label: "Cancel",
                        action: { name: "cancel" },
                      },
                    ]}
                  />
                </State>
              ))}
            </Cell>
          ))}
        </Family>
      ))}
    </div>
  );
}
