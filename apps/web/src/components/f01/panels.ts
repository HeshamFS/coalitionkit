// SPDX-License-Identifier: Apache-2.0
// Panel labels and summaries as drawn in the component sheet.
export const panels = [
  {
    span: 1,
    "cell-name": "Button · variants",
    props:
      "variant: primary | secondary | ink | soft | ghost | danger | danger-fill · label · icon? · action",
    evts: "→ action.invoke(id)",
  },
  {
    span: 1,
    "cell-name": "Button · states",
    props:
      "state: default | hover | pressed | focus | busy | disabled · disabledReason (always shown)",
  },
  {
    span: 1,
    "cell-name": "Button · sizes · IconButton",
    props: "size: sm 28 | md 32 | lg 44 (touch) · IconButton.label required (tooltip + aria-label)",
  },
  {
    span: 1,
    "cell-name": "ButtonGroup · SplitButton",
    props: "items[] {label, value, hint?, disabled?} · primary item · menu opens below, 4 px gap",
  },
  {
    span: 1,
    "cell-name": "TextField · every state",
    props:
      "label · value (path) · placeholder · help? · error? · readOnly · private (vault) · maxLength",
    evts: "→ field.change(value) · field.submit",
  },
  {
    span: 1,
    "cell-name": "TextArea · mention",
    props: "rows 3-8 · maxLength · mentions: participant ids · scope chip under the field",
  },
  {
    span: 1,
    "cell-name": "NumberField · units",
    props: "min · max · step · unit · currency? · private: answer-only (vault answers yes/no)",
  },
  {
    span: 1,
    "cell-name": "SearchField · suggestions",
    props: "query · groups[] {label, items[]} · highlights the match · keyboard: ↑ ↓ enter esc",
  },
  {
    span: 1,
    "cell-name": "Select · closed and open",
    props:
      "options[] {value, label, hint?, disabled?} · value · placeholder · opens on click, ↓ or type-ahead",
  },
  {
    span: 1,
    "cell-name": "ChoicePicker · multi",
    props: "multiple · options[] · max? · chips removable · variant: list | chips | cards",
  },
  {
    span: 1,
    "cell-name": "CheckBox · RadioGroup",
    props: "checked | indeterminate | unchecked · description? · disabledReason",
  },
  {
    span: 1,
    "cell-name": "Switch · settings list",
    props: "on · label · description · confirm? (a switch that grants data asks first)",
  },
  {
    span: 1,
    "cell-name": "Slider · range with floor",
    props: "min · max · step · value | [lo, hi] · marks[] {at, label, tone} · unit · format",
  },
  {
    span: 1,
    "cell-name": "SegmentedControl · Tabs",
    props: "items[] {id, label, count?} · selected · variant: segmented | underline | chips",
    evts: "→ tab.select(id)",
  },
  {
    span: 2,
    "cell-name": "FilterBar · sort and group",
    props:
      "query · filters[] {field, op, value} · sort {field, dir} · groupBy? · resultCount (from host)",
  },
  {
    span: 1,
    "cell-name": "DateTimeInput · open calendar",
    props: "mode: date | time | datetime | range · min · max · busy[] (from PSI, no names) · tz",
  },
  {
    span: 2,
    "cell-name": "SlotPicker · overlap of private calendars",
    props:
      "days[] {date, slots[] {start, state: free | mine | shared | off}} · selected · duration · source: psi_match (counts only)",
    evts: "→ slot.hold(start) · slot.release(start)",
  },
  {
    span: 1,
    "cell-name": "Deadline · TimeZone",
    props: "deadline (ISO) · tone by remaining: calm > 1 h · ask < 1 h · bad passed · viewer tz",
  },
  {
    span: 1,
    "cell-name": "Tooltip",
    props: "text ≤ 80 chars · shows on hover 400 ms, focus, long-press · never holds actions",
  },
  {
    span: 1,
    "cell-name": "Popover · participant card",
    props: "anchor · title · body (catalog components) · actions[] ≤ 2 · closes on esc / outside",
  },
  {
    span: 1,
    "cell-name": "Menu · context",
    props:
      "items[] {label, icon?, shortcut?, submenu?, tone: default | danger, disabled?} · groups split by rules",
  },
  {
    span: 1,
    "cell-name": "Modal · confirm",
    props:
      "title · body · consequence (required for irreversible) · confirm {label, tone} · cancel · focus trap",
  },
  {
    span: 1,
    "cell-name": "Sheet · phone",
    props: "detents: peek | half | full · title · body · actions[] · drag to dismiss",
  },
  {
    span: 1,
    "cell-name": "Drawer · side",
    props:
      "side: right | left · width 360-480 · title · body · footer actions · modal: false (canvas stays live)",
  },
  {
    span: 1,
    "cell-name": "Toast · stack",
    props:
      "tone: done | change | error · text ≤ 60 · action? · undoWindow (s) · max 3, newest on top",
  },
  {
    span: 1,
    "cell-name": "Banner · inline alert",
    props: "tone: info | ask | blocked | agreed · title · body · action? · dismissible",
  },
  {
    span: 1,
    "cell-name": "Progress · four forms",
    props: "variant: bar | segments | steps | ring · value · max · label · indeterminate",
  },
  {
    span: 1,
    "cell-name": "Skeleton · loading card",
    props:
      "shape follows the component it stands for · label for screen readers · after 8 s say what is slow",
  },
  {
    span: 1,
    "cell-name": "EmptyState",
    props: "glyph · title · body · action? · never blank: say what fills it and who",
  },
  {
    span: 1,
    "cell-name": "ErrorState · Reconnecting",
    props: "cause (plain words) · lastSeen · retry · details (error code, ref) · offline bar",
  },
  {
    span: 2,
    "cell-name": "CommandPalette",
    props:
      "query · groups: actions | objects | log | ask · each item names its kind · last group hands the words to your agent",
  },
  {
    span: 2,
    "cell-name": "Table · sort, select, row status",
    props:
      "columns[] {key, label, align, sortable, format} · rows (path) · selection: none | one | many · rowTone · pageSize · redacted cells keep their width",
  },
  {
    span: 1,
    "cell-name": "List · with meta",
    props:
      "items[] {leading, title, meta, trailing} · divider · unread marker · virtualised past 50",
  },
  {
    span: 1,
    "cell-name": "KeyValue · Badge · Tag",
    props:
      "Tag = state (5 words only) · Badge = where a value came from · Scope chip = who sees it",
  },
  {
    span: 1,
    "cell-name": "Avatar · presence · stack",
    props:
      "seat 1-5 colour · square = host or steward · presence: live | away | off · ring = speaking or acting",
  },
  {
    span: 1,
    "cell-name": "Chip · Link · Divider · Kbd",
    props:
      "Chip: label · selected · removable · seat? · Link: href (host-resolved) | logRef · Divider: label?",
  },
  {
    span: 1,
    "cell-name": "Image · three states",
    props:
      "src (host-resolved in scope) · alt required · caption? · evidence id? · fit: cover | contain",
  },
  {
    span: 1,
    "cell-name": "Video · captions",
    props: "src · poster · captions (required when speech) · chapters[]? · evidence id?",
    evts: "→ media.play · media.pause · media.seek(t)",
  },
  {
    span: 1,
    "cell-name": "AudioPlayer · voice note",
    props: "src · duration · transcript (path) · speaker? · speed 1 | 1.5 | 2",
  },
  {
    span: 1,
    "cell-name": "FileDrop · files",
    props:
      "accept[] · maxBytes · destination: vault | coalition (asks) · states: idle | over | uploading | done | failed",
    evts: "→ file.add(ref) · file.remove(ref)",
  },
];
