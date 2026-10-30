// SPDX-License-Identifier: Apache-2.0
import type { Door } from "../../gallery/Cell";
export const metadata: Record<string, { doors: Door[]; events: string[]; states: string[] }> = {
  AudioPlayer: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["media.play", "media.pause", "media.seek(t)"],
    states: ["paused", "playing"],
  },
  Avatar: {
    doors: ["wide", "compact", "lens", "message"],
    events: [],
    states: ["default", "speaking"],
  },
  AvatarStack: {
    doors: ["wide", "compact"],
    events: [],
    states: ["default"],
  },
  Badge: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["default"],
  },
  Banner: {
    doors: ["wide", "compact", "message"],
    events: ["banner.action", "banner.dismiss"],
    states: ["shown"],
  },
  Button: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: ["action.name(context)"],
    states: ["default", "hover", "focus", "disabled", "busy"],
  },
  ButtonGroup: {
    doors: ["wide", "compact", "lens"],
    events: ["action.name(context)"],
    states: ["default"],
  },
  Card: {
    doors: ["wide", "compact", "lens"],
    events: ["open(subject)"],
    states: ["default", "live", "ask"],
  },
  CheckBox: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["change(value)"],
    states: ["off", "on", "disabled"],
  },
  Chip: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: ["select(id)"],
    states: ["default", "selected"],
  },
  ChoicePicker: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["select(value)"],
    states: ["none", "one", "many"],
  },
  Column: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["default"],
  },
  CommandPalette: {
    doors: ["wide"],
    events: ["command.run(id)", "command.ask(text)"],
    states: ["open", "results", "empty"],
  },
  DateTimeInput: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["change(value)"],
    states: ["empty", "filled", "error"],
  },
  Deadline: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["calm", "ask", "passed"],
  },
  Divider: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["default"],
  },
  Drawer: {
    doors: ["wide"],
    events: ["drawer.close"],
    states: ["open"],
  },
  EmptyState: {
    doors: ["wide", "compact"],
    events: ["action.invoke"],
    states: ["default"],
  },
  ErrorState: {
    doors: ["wide", "compact"],
    events: ["error.retry"],
    states: ["error", "reconnecting"],
  },
  FileDrop: {
    doors: ["wide", "compact"],
    events: ["file.add(file)"],
    states: ["idle", "dragover", "uploading", "error"],
  },
  FilterBar: {
    doors: ["wide", "compact"],
    events: ["filter.change", "sort.change"],
    states: ["default", "filtered"],
  },
  Grid: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["default"],
  },
  Heading: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["default"],
  },
  Icon: {
    doors: ["wide", "compact", "lens"],
    events: [],
    states: ["default"],
  },
  IconButton: {
    doors: ["wide", "compact", "lens"],
    events: ["action.name(context)"],
    states: ["default", "hover", "focus", "disabled"],
  },
  Image: {
    doors: ["wide", "compact", "message"],
    events: [],
    states: ["loading", "loaded", "failed"],
  },
  KeyValue: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["default"],
  },
  Link: {
    doors: ["wide", "compact", "message"],
    events: ["link.open(href)"],
    states: ["default", "hover", "focus", "visited"],
  },
  List: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: ["open(item)", "select(item)"],
    states: ["empty", "filled"],
  },
  Menu: {
    doors: ["wide", "compact"],
    events: ["menu.pick(id)"],
    states: ["open", "item-hover", "submenu"],
  },
  Meter: {
    doors: ["wide", "compact", "lens", "voice"],
    events: [],
    states: ["ok", "warn", "bad"],
  },
  Modal: {
    doors: ["wide"],
    events: ["dismiss"],
    states: ["closed", "open"],
  },
  NumberField: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["change(value, unit)"],
    states: ["empty", "filled", "focus", "error"],
  },
  Panel: {
    doors: ["wide", "compact", "lens"],
    events: [],
    states: ["default"],
  },
  Popover: {
    doors: ["wide"],
    events: ["popover.close"],
    states: ["open"],
  },
  Progress: {
    doors: ["wide", "compact", "lens", "voice"],
    events: [],
    states: ["determinate", "stepped", "indeterminate"],
  },
  RadioGroup: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["change(value)"],
    states: ["none", "selected"],
  },
  RichText: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["link.open(href)"],
    states: ["default"],
  },
  Row: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["default"],
  },
  SearchField: {
    doors: ["wide", "compact"],
    events: ["search.change(q)", "search.pick(id)"],
    states: ["empty", "typing", "results", "no-results"],
  },
  SegmentedControl: {
    doors: ["wide", "compact", "message"],
    events: ["select(value)"],
    states: ["pressed", "unpressed"],
  },
  Sheet: {
    doors: ["compact"],
    events: ["dismiss"],
    states: ["closed", "open"],
  },
  Skeleton: {
    doors: ["wide", "compact"],
    events: [],
    states: ["skeleton", "filled", "live", "rest", "changed"],
  },
  Slider: {
    doors: ["wide", "compact"],
    events: ["change(value)"],
    states: ["default", "focus", "disabled"],
  },
  SlotPicker: {
    doors: ["wide", "compact"],
    events: ["slot.hold(start)", "slot.release(start)"],
    states: ["loading", "ready", "held", "none-shared"],
  },
  Spinner: {
    doors: ["wide", "compact", "lens"],
    events: [],
    states: ["spinning"],
  },
  SplitButton: {
    doors: ["wide", "compact"],
    events: ["action.invoke(value)"],
    states: ["closed", "open"],
  },
  Switch: {
    doors: ["wide", "compact"],
    events: ["change(value)"],
    states: ["off", "on", "disabled"],
  },
  Table: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["sort(key)", "open(row)"],
    states: ["empty", "filled"],
  },
  Tabs: {
    doors: ["wide", "compact", "message"],
    events: ["select(value)"],
    states: ["selected", "unselected"],
  },
  Tag: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["agreed", "needs", "changed", "private", "blocked"],
  },
  Text: {
    doors: ["wide", "compact", "lens", "message", "voice"],
    events: [],
    states: ["default"],
  },
  TextArea: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["change(value)"],
    states: ["empty", "filled", "focus", "error", "disabled"],
  },
  TextField: {
    doors: ["wide", "compact", "message", "voice"],
    events: ["change(value)", "submit(value)"],
    states: ["empty", "filled", "focus", "error", "disabled"],
  },
  TimeZone: {
    doors: ["wide", "compact"],
    events: ["tz.change"],
    states: ["default"],
  },
  Toast: {
    doors: ["wide", "compact", "lens"],
    events: ["toast.action", "toast.undo"],
    states: ["shown", "stacked", "dismissed"],
  },
  Tooltip: {
    doors: ["wide"],
    events: [],
    states: ["hidden", "shown"],
  },
  Video: {
    doors: ["wide", "compact"],
    events: ["media.play", "media.pause", "media.seek(t)"],
    states: ["paused", "playing"],
  },
};
