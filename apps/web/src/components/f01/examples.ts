// SPDX-License-Identifier: Apache-2.0
type Example = { props: Record<string, unknown>; data?: Record<string, unknown>; label?: string };
const bound = (value: number) => ({ value, event_ref: "example" });
const options = [
  { id: "a", label: "Resource 1" },
  { id: "b", label: "Resource 2" },
  { id: "c", label: "Resource 3" },
];
const people = ["A", "B", "C", "D", "E"].map((label, i) => ({
  label: `Member ${label}`,
  seat: String(i + 1),
}));
const value = (v: unknown, props: Record<string, unknown> = {}): Example => ({
  props: { ...props, value: { path: "/value" } },
  data: { value: v },
});
const base: Record<string, Example> = {
  Button: {
    props: {
      label: "Propose plan",
      variant: "primary",
      action: { name: "plan.propose", context: { id: "p1" } },
    },
  },
  IconButton: { props: { ariaLabel: "Add", icon: "plus", action: { name: "add" } } },
  ButtonGroup: { props: { children: ["action1", "action2"] } },
  SplitButton: {
    props: {
      primary: "propose",
      items: [
        { label: "Propose plan", value: "propose" },
        { label: "Save draft", value: "draft", hint: "Keep for later" },
      ],
    },
  },
  TextField: value("", { label: "Coalition name", placeholder: "Give this coalition a name" }),
  TextArea: value("I can help with Task 3. @Member A", {
    label: "Your offer",
    maxLength: bound(500),
  }),
  NumberField: value(42, {
    label: "Your limit",
    unit: "EUR",
    min: bound(0),
    max: bound(100),
    step: bound(1),
  }),
  SearchField: {
    props: { query: { path: "/query" }, groups: [{ label: "Offers", items: options }] },
    data: { query: "Resource" },
  },
  ChoicePicker: value(["a", "b"], { multiple: true, options }),
  CheckBox: value(true, { label: "Share with the coalition" }),
  RadioGroup: value("a", { options }),
  Switch: value(true, { label: "Let your agent propose" }),
  Slider: value(42, { min: bound(0), max: bound(100), step: bound(1), unit: "EUR" }),
  SegmentedControl: value("a", {
    options: [
      { id: "a", label: "All" },
      { id: "b", label: "Needs you" },
      { id: "c", label: "Agreed" },
    ],
  }),
  Tabs: value("a", {
    options: [
      { id: "a", label: "Offers" },
      { id: "b", label: "Plans" },
      { id: "c", label: "Log" },
    ],
    panels: ["body"],
  }),
  FilterBar: {
    props: {
      query: { path: "/q" },
      resultCount: { path: "/count" },
      filters: [{ field: "Status", op: "is", value: "Open" }],
      sort: { field: "Updated", dir: "desc" },
    },
    data: { q: "", count: "12" },
  },
  DateTimeInput: value("2026-10-30T22:30", { mode: "datetime", tz: "UTC" }),
  SlotPicker: {
    props: {
      days: [
        {
          date: "Mon 19",
          slots: [
            { start: "09:00", state: "free" },
            { start: "09:30", state: "shared" },
            { start: "10:00", state: "off" },
          ],
        },
        {
          date: "Tue 20",
          slots: [
            { start: "11:00", state: "mine" },
            { start: "11:30", state: "shared" },
            { start: "12:00", state: "off" },
          ],
        },
      ],
      duration: bound(30),
      selected: "09:30",
      source: "psi_match",
    },
  },
  Deadline: {
    props: {
      label: "Decision closes at 22:40",
      deadline: "2026-10-30T22:40:00Z",
      consequence: "After this the offer expires",
    },
  },
  TimeZone: {
    props: {
      value: "UTC",
      others: [
        { participant: "Member A", tz: "Europe/Berlin" },
        { participant: "Member B", tz: "UTC" },
      ],
    },
  },
  Tooltip: { props: { target: "tooltip-target", tip: "Only the coalition sees this" } },
  Popover: { props: { title: "Member A", anchor: "member-a", body: ["body"], actions: bound(2) } },
  Menu: {
    props: {
      items: [
        { id: "open", label: "Open details", shortcut: "↵" },
        { id: "copy", label: "Copy reference" },
        { id: "withdraw", label: "Withdraw offer", tone: "danger" },
        { id: "locked", label: "Blocked by charter", disabled: true },
      ],
    },
  },
  Modal: {
    props: {
      title: "Withdraw your offer?",
      open: { path: "/open" },
      dismissible: true,
      children: ["body", "action1", "action2"],
    },
    data: { open: true },
  },
  Sheet: {
    props: {
      title: "Your part",
      open: { path: "/open" },
      dismissible: true,
      children: ["body", "action1"],
    },
    data: { open: true },
  },
  Drawer: {
    props: {
      title: "Offer details",
      body: ["body"],
      footer: ["action1"],
      side: "right",
      width: bound(380),
    },
  },
  Toast: { props: { text: "Offer added to the plan", tone: "done", action: { label: "View" } } },
  Banner: {
    props: {
      title: "The plan changed",
      body: "Review what this changes for you.",
      tone: "info",
      action: { label: "Review" },
    },
  },
  Progress: {
    props: { label: "Uploading the file", value: bound(68), max: bound(100), unit: "%" },
  },
  Meter: {
    props: {
      label: "Capacity",
      value: bound(64),
      max: bound(100),
      unit: "%",
      bands: [
        { upTo: bound(70), tone: "ok" },
        { upTo: bound(90), tone: "warn" },
        { upTo: bound(100), tone: "bad" },
      ],
    },
  },
  Skeleton: { props: { shape: "card" } },
  Spinner: { props: { label: "Your agent is reading the offers" } },
  EmptyState: {
    props: {
      title: "No offers yet",
      body: "When someone can help with a need, it shows up here. Your agent is listening.",
      glyph: "plus",
      action: { label: "Add what you can offer" },
    },
  },
  ErrorState: {
    props: {
      cause: "Can't reach your agent",
      lastSeen: "2026-10-30T21:58:00Z",
      retry: true,
      details: { code: "OFFLINE", ref: "r1" },
    },
  },
  CommandPalette: { props: { query: { path: "/query" }, groups: "ask" }, data: { query: "prop" } },
  Table: {
    props: {
      columns: [
        { key: "offer", label: "Offer" },
        { key: "from", label: "From" },
        { key: "when", label: "When" },
        { key: "status", label: "Status" },
        { key: "cost", label: "Cost", align: "right" },
      ],
      rows: { path: "/rows" },
      sortable: true,
    },
    data: {
      rows: [
        {
          id: "o1",
          offer: "Resource 1, 3 units",
          from: "Member A",
          when: "22:30",
          status: "Agreed",
          cost: "≈ €42",
        },
        {
          id: "o2",
          offer: "Resource 2, 2 units",
          from: "Member B",
          when: "22:10",
          status: "Needs you",
          cost: "[vault]",
        },
        {
          id: "o3",
          offer: "Resource 3",
          from: "Member C",
          when: "21:58",
          status: "Changed",
          cost: "€0",
        },
      ],
    },
  },
  List: {
    props: { items: { path: "/items" }, selectable: true },
    data: {
      items: [
        { id: "p1", title: "Member A", meta: "offered a resource", trailing: "2 m" },
        { id: "p2", title: "Member B", meta: "needs a resource before 01:00", trailing: "live" },
        { id: "host", title: "Host", meta: "signed receipt #41", trailing: "5 m" },
      ],
    },
  },
  KeyValue: {
    props: {
      pairs: [
        { label: "Coalition", value: "Shared task" },
        { label: "Stage", value: "Decide" },
        { label: "Members", value: "3 people, 4 agents" },
        { label: "Charter", value: "revision 3 · signed" },
      ],
    },
  },
  Badge: { props: { kind: "measured", label: "Measured" } },
  Tag: { props: { kind: "agreed", label: "Agreed" } },
  Avatar: { props: { label: "Member A", seat: "1", presence: "live", size: "lg" } },
  AvatarStack: { props: { people, max: bound(3) } },
  Chip: { props: { label: "Resource 1", selected: true } },
  Link: { props: { text: "Read the charter", href: "https://example.org/charter" } },
  Divider: { props: {} },
  Image: { props: { alt: "Resource preview", src: { path: "/src" } }, data: { src: "" } },
  Video: {
    props: { src: { path: "/src" }, captions: { path: "/captions" } },
    data: { src: "", captions: "" },
  },
  AudioPlayer: {
    props: { title: "Member A · voice note", src: { path: "/src" } },
    data: { src: "" },
  },
  FileDrop: {
    props: {
      accept: ["application/pdf", "image/*", "text/csv"],
      maxBytes: bound(20000000),
      target: { path: "/files" },
    },
    data: { files: [] },
  },
  Heading: { props: { text: "A plan everyone can stand behind", variant: "h1" } },
  Text: { props: { text: "Your agent brings the options. You decide.", variant: "body" } },
  RichText: { props: { markdown: "A **shared** plan, with your consent.", allow: "bold" } },
  Icon: { props: { name: "shieldCheck", label: "Verified", size: "24", tone: "blue" } },
  Row: { props: { children: ["action1", "action2"], gap: "8" } },
  Column: { props: { children: ["body", "action1"], gap: "8" } },
  Grid: { props: { children: ["body", "action1"], columns: bound(2), gap: "12" } },
  Card: { props: { title: "Plan A", tone: "live", scope: "coalition", children: ["body"] } },
  Panel: { props: { title: "Your coalition", scope: "coalition", children: ["body"] } },
};

export function examples(name: string): Example[] {
  const sample = base[name] ?? { props: {} };
  const variations: Record<string, [string, string[]]> = {
    Button: ["variant", ["primary", "secondary", "ink", "ghost"]],
    Tag: ["kind", ["agreed", "needs", "changed", "private", "blocked"]],
    Badge: ["kind", ["measured", "signed", "vault", "model", "estimate"]],
    Banner: ["tone", ["info", "ask", "blocked", "agreed"]],
    Toast: ["tone", ["done", "change", "error"]],
    Avatar: ["size", ["xs", "sm", "lg", "xl"]],
    Card: ["tone", ["default", "live", "ask", "dashed"]],
    Heading: ["variant", ["h1", "h2", "h3"]],
    Skeleton: ["shape", ["card", "line", "block", "avatar"]],
  };
  const special = specialExamples(name, sample);
  if (special) return special;
  const variation = variations[name];
  if (variation)
    return variation[1].map((v) => ({
      ...sample,
      props: {
        ...sample.props,
        [variation[0]]: v,
        ...(name === "Tag" || name === "Badge"
          ? { label: v === "needs" ? "Needs you" : v[0]?.toUpperCase() + v.slice(1) }
          : {}),
      },
      label: v,
    }));
  if (name === "TextField" || name === "TextArea")
    return [
      value("", sample.props),
      value("Shared task", sample.props),
      {
        ...value("Shared task", { ...sample.props, error: { path: "/error" } }),
        data: { value: "Shared task", error: "This name is already in use" },
        label: "error",
      },
    ];
  if (name === "CheckBox" || name === "Switch")
    return [value(false, sample.props), value(true, sample.props)];
  return [sample];
}

function specialExamples(name: string, sample: Example): Example[] | undefined {
  if (name === "Button")
    return [
      ...["primary", "secondary", "ink", "ghost"].map((variant) => ({
        ...sample,
        props: { ...sample.props, variant },
        label: variant,
      })),
      ...["sm", "md", "lg"].map((size) => ({
        ...sample,
        props: { ...sample.props, size },
        label: size,
      })),
      { ...sample, props: { ...sample.props, disabled: true }, label: "disabled" },
      { ...sample, props: { ...sample.props, busy: true }, label: "busy" },
    ];
  if (name === "Avatar")
    return [
      ...["xs", "sm", "lg", "xl"].map((size) => ({
        ...sample,
        props: { ...sample.props, size },
        label: size,
      })),
      ...["live", "away", "off"].map((presence) => ({
        ...sample,
        props: { ...sample.props, presence },
        label: presence,
      })),
      {
        ...sample,
        props: { ...sample.props, ring: true, seat: "4", label: "Member D" },
        label: "speaking",
      },
      { ...sample, props: { ...sample.props, seat: "host", label: "Host" }, label: "host" },
    ];
  if (name === "ChoicePicker")
    return [
      value("", { options, display: "menu" }),
      value("a", { options, display: "menu" }),
      sample,
    ];
  if (name === "Progress")
    return [
      sample,
      {
        props: { label: "Waiting for answers", value: bound(2), max: bound(3), steps: bound(3) },
        label: "stepped",
      },
    ];
  if (name === "Toast")
    return [
      ...["done", "change", "error"].map((tone) => ({
        ...sample,
        props: { ...sample.props, tone },
        label: tone,
      })),
      { props: { text: "Offer withdrawn", tone: "done", undoWindow: bound(5) }, label: "undo" },
    ];
  if (name === "Deadline")
    return [
      {
        props: {
          label: "Decision at 22:40",
          deadline: "2099-10-30T22:40:00Z",
          consequence: "After this the offer expires",
        },
        label: "calm",
      },
      {
        props: {
          label: "Decision in 12 min",
          deadline: new Date(Date.now() + 720000).toISOString(),
          consequence: "After this the offer expires",
        },
        label: "ask",
      },
      {
        props: {
          label: "Decision closed",
          deadline: "2020-10-30T22:40:00Z",
          consequence: "The offer expired",
        },
        label: "passed",
      },
    ];
  return undefined;
}
