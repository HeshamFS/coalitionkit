// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apis } from "../../catalog/families/f01";
import { SurfaceBook } from "../../feed/surfaces";
import { examples, Sheet01 } from "../../gallery/sheets/Sheet01";

afterEach(cleanup);
function draw(
  name: string,
  props?: Record<string, unknown>,
  data?: Record<string, unknown>,
  children: Record<string, unknown>[] = [],
) {
  const dispatch = vi.fn();
  const book = new SurfaceBook(dispatch);
  const example = examples(name)[0];
  book.apply("test", [
    { version: "v0.9", createSurface: { surfaceId: "test", catalogId: "coalitionkit/v0_9" } },
    {
      version: "v0.9",
      updateComponents: {
        surfaceId: "test",
        components: [{ id: "root", component: name, ...(props ?? example?.props) }, ...children],
      },
    },
    {
      version: "v0.9",
      updateDataModel: { surfaceId: "test", path: "/", value: data ?? example?.data ?? {} },
    },
  ]);
  const surface = book.list()[0];
  expect(surface?.fallback).toBe(false);
  const view = render(<A2uiSurface surface={required(surface).model} />);
  return { dispatch, ...view };
}
function event(
  dispatch: ReturnType<typeof vi.fn>,
  name: string,
  context: Record<string, unknown> = {},
) {
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({ name, context: expect.objectContaining(context) }),
  );
}
function required<T>(value: T | null | undefined): T {
  if (value == null) throw new Error("Expected a rendered value");
  return value;
}
it("draws every family 01 component through the catalog without fallback", () => {
  const { container } = render(<Sheet01 />);
  expect(container.querySelector("[data-fallback]")).toBeNull();
  for (const api of apis)
    expect(container.querySelector(`.f01[data-component="${api.name}"]`)).not.toBeNull();
}, 30000);
describe("catalog actions", () => {
  it.each(["Button", "IconButton"])("%s dispatches its named action with context", (name) => {
    const { dispatch } = draw(name, {
      label: "Run",
      ariaLabel: "Run",
      action: { name: "task.run", context: { id: "t1" } },
    });
    fireEvent.click(screen.getByRole("button"));
    event(dispatch, "task.run", { id: "t1" });
  });
  it.each(["TextField", "TextArea", "NumberField", "DateTimeInput", "Slider"])(
    "%s emits change",
    (name) => {
      const { dispatch, container } = draw(name);
      const field = required(container.querySelector("input,textarea"));
      const value =
        name === "DateTimeInput"
          ? "2026-10-30T10:00"
          : name === "NumberField" || name === "Slider"
            ? "25"
            : "New value";
      fireEvent.change(field, { target: { value } });
      event(dispatch, "change", {
        value: name === "NumberField" || name === "Slider" ? 25 : value,
      });
      if (name === "TextField") {
        fireEvent.keyDown(field, { key: "Enter" });
        event(dispatch, "submit", { value });
      }
    },
  );
  it.each(["CheckBox", "Switch"])("%s emits a boolean", (name) => {
    const { dispatch } = draw(name);
    fireEvent.click(screen.getByRole(name === "Switch" ? "switch" : "checkbox"));
    event(dispatch, "change", { value: true });
  });
  it.each(["ChoicePicker", "SegmentedControl", "Tabs", "RadioGroup"])(
    "%s emits selection",
    (name) => {
      const { dispatch, container } = draw(name);
      if (name === "ChoicePicker")
        fireEvent.change(screen.getByRole("combobox"), { target: { value: "c" } });
      else
        fireEvent.click(
          required(container.querySelectorAll(name === "RadioGroup" ? "input" : "button")[2]),
        );
      event(dispatch, name === "RadioGroup" ? "change" : "select");
    },
  );
  it("Chip emits its component id", () => {
    const { dispatch } = draw("Chip");
    fireEvent.click(screen.getByRole("button"));
    event(dispatch, "select", { id: "root" });
  });
  it("Link is host resolved", () => {
    const { dispatch } = draw("Link");
    fireEvent.click(screen.getByRole("link"));
    event(dispatch, "link.open", { href: "https://example.org/charter" });
  });
  it("RichText emits link.open without interpreting HTML", () => {
    const { dispatch } = draw("RichText", {
      allow: "link",
      markdown: "<script> [Read](https://example.org)",
    });
    fireEvent.click(screen.getByRole("link"));
    event(dispatch, "link.open");
    expect(screen.getByText(/<script>/)).toBeTruthy();
  });
  it("SearchField supports query and keyboard picking", () => {
    const { dispatch } = draw("SearchField");
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Resource 2" } });
    event(dispatch, "search.change", { q: "Resource 2" });
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter" });
    event(dispatch, "search.pick", { id: "b" });
  });
  it("CommandPalette asks the agent", () => {
    const { dispatch } = draw("CommandPalette");
    fireEvent.click(screen.getByRole("button"));
    event(dispatch, "command.ask", { text: "prop" });
  });
  it("FilterBar emits query and sort changes", () => {
    const { dispatch } = draw("FilterBar");
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "open" } });
    event(dispatch, "filter.change");
    fireEvent.click(screen.getByRole("button"));
    event(dispatch, "sort.change", { dir: "asc" });
  });
  it.each(["Modal", "Sheet", "Drawer", "Popover"])("%s closes by keyboard", (name) => {
    const { dispatch } = draw(name);
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    event(
      dispatch,
      name === "Drawer" ? "drawer.close" : name === "Popover" ? "popover.close" : "dismiss",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });
  it("Menu disables unavailable items", () => {
    const { dispatch } = draw("Menu");
    fireEvent.click(screen.getByText("Blocked by charter"));
    expect(dispatch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Open details"));
    event(dispatch, "menu.pick", { id: "open" });
  });
  it("SplitButton invokes primary and menu values", () => {
    const { dispatch } = draw("SplitButton");
    fireEvent.click(screen.getByText("Propose plan"));
    event(dispatch, "action.invoke", { value: "propose" });
    fireEvent.click(screen.getByLabelText("More actions"));
    fireEvent.click(screen.getByText("Save draft"));
    event(dispatch, "action.invoke", { value: "draft" });
  });
  it("Table sorts and opens rows", () => {
    const { dispatch } = draw("Table");
    fireEvent.click(screen.getByText("When ↕"));
    event(dispatch, "sort", { key: "when" });
    fireEvent.click(screen.getByText("Resource 1, 3 units"));
    event(dispatch, "open");
  });
  it("List opens and selects items", () => {
    const { dispatch } = draw("List");
    fireEvent.click(screen.getByText("Member A"));
    event(dispatch, "open");
    fireEvent.click(required(screen.getAllByRole("checkbox")[0]));
    event(dispatch, "select");
  });
  it("SlotPicker releases and holds", () => {
    const { dispatch } = draw("SlotPicker");
    fireEvent.click(screen.getByText("09:30"));
    event(dispatch, "slot.release", { start: "09:30" });
    fireEvent.click(screen.getByText("09:30"));
    event(dispatch, "slot.hold", { start: "09:30" });
  });
  it("TimeZone emits tz.change", () => {
    const { dispatch } = draw("TimeZone");
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "Europe/Berlin" } });
    event(dispatch, "tz.change", { value: "Europe/Berlin" });
  });
  it.each([
    ["Banner", "Review", "banner.action"],
    ["Toast", "View", "toast.action"],
    ["EmptyState", "Add what you can offer", "action.invoke"],
    ["ErrorState", "Try again", "error.retry"],
  ])("%s emits its action", (name, label, evt) => {
    const { dispatch } = draw(required(name));
    fireEvent.click(screen.getByText(required(label)));
    event(dispatch, required(evt));
  });
  it("Banner dismisses", () => {
    const { dispatch } = draw("Banner");
    fireEvent.click(screen.getByLabelText("Dismiss"));
    event(dispatch, "banner.dismiss");
  });
  it("Toast undo emits only while available", () => {
    const { dispatch } = draw("Toast", {
      text: "Changed",
      tone: "change",
      undoWindow: { value: 5, event_ref: "e1" },
    });
    fireEvent.click(screen.getByRole("button"));
    event(dispatch, "toast.undo");
  });
  it.each(["Video", "AudioPlayer"])("%s emits playback events", (name) => {
    const { dispatch, container } = draw(name);
    const media = required(container.querySelector("video,audio"));
    fireEvent.play(media);
    event(dispatch, "media.play");
    fireEvent.pause(media);
    event(dispatch, "media.pause");
    fireEvent.seeked(media);
    event(dispatch, "media.seek", { t: 0 });
  });
  it("FileDrop validates size before dispatch", () => {
    const { dispatch, container } = draw("FileDrop", { maxBytes: { value: 3, event_ref: "e1" } });
    fireEvent.change(required(container.querySelector("input")), {
      target: { files: [new File(["large"], "large.txt")] },
    });
    expect(dispatch).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeTruthy();
    fireEvent.change(required(container.querySelector("input")), {
      target: { files: [new File(["ok"], "small.txt")] },
    });
    event(dispatch, "file.add");
  });
});

it("ButtonGroup dispatches the child action through the catalog", () => {
  const { dispatch } = draw("ButtonGroup", { children: ["child"] }, {}, [
    {
      id: "child",
      component: "Button",
      label: "Run",
      action: { name: "task.run", context: { id: "t1" } },
    },
  ]);
  fireEvent.click(screen.getByRole("button"));
  event(dispatch, "task.run", { id: "t1" });
});
it("Card emits an open subject", () => {
  const { dispatch } = draw("Card", { title: "Task card" });
  fireEvent.click(screen.getByRole("button", { name: "Open" }));
  event(dispatch, "open", { subject: { kind: "card", id: "root" } });
});
it("Button preserves existing A2UI event envelopes", () => {
  const { dispatch } = draw("Button", {
    label: "Open",
    action: { event: { name: "open", context: { id: "t1" } } },
  });
  fireEvent.click(screen.getByRole("button"));
  event(dispatch, "open", { id: "t1" });
});
it("CommandPalette runs host-provided results", () => {
  const { dispatch } = draw(
    "CommandPalette",
    { query: { path: "/query" }, groups: "actions" },
    {
      query: {
        text: "Plan",
        groups: [{ label: "Actions", items: [{ id: "p1", label: "Plan details" }] }],
      },
    },
  );
  fireEvent.click(screen.getByRole("button", { name: "Plan details" }));
  event(dispatch, "command.run", { id: "p1" });
});

it("Tooltip follows its catalog target on focus and blur", () => {
  draw("Column", { children: ["target", "tip"] }, {}, [
    { id: "target", component: "Button", label: "Audience" },
    { id: "tip", component: "Tooltip", target: "target", tip: "Only coalition members" },
  ]);
  expect(screen.queryByRole("tooltip")).toBeNull();
  fireEvent.focus(screen.getByRole("button"));
  expect(screen.getByRole("tooltip")).toHaveTextContent("Only coalition members");
  fireEvent.blur(screen.getByRole("button"));
  expect(screen.queryByRole("tooltip")).toBeNull();
});
