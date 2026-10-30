// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";
import { Drawn, type Node, One } from "../../gallery/Drawn";

const bound = (value: number) => ({ value, event_ref: "example" });
const text = (id: string, content: string): Node => ({
  id,
  component: "Text",
  text: content,
  variant: "caption",
  tone: "muted",
});
const button = (id: string, label: string, variant = "secondary", size = "sm"): Node => ({
  id,
  component: "Button",
  label,
  variant,
  size,
  action: { name: id },
});
export function OverlayPanels({ index }: { index: number }) {
  return demos[index]?.() ?? null;
}

const demos: Record<number, () => ReactNode> = {
  19: () => (
    <>
      <div className="row">
        <One
          component="Avatar"
          props={{ label: "Member B", seat: "2", size: "lg", presence: "live" }}
        />
        <span className="small">hover a seat →</span>
      </div>
      <Drawn
        components={[
          {
            id: "root",
            component: "Popover",
            title: "",
            body: ["identity", "chips", "fields", "actions"],
          },
          { id: "identity", component: "Row", children: ["avatar", "details"] },
          { id: "details", component: "Column", gap: "4", children: ["name", "caption"] },
          { id: "name", component: "RichText", allow: "bold", markdown: "**Member B**" },
          { id: "avatar", component: "Avatar", label: "Member B", seat: "2", size: "lg" },
          text("caption", "agent on a server · joined 21:31"),
          { id: "chips", component: "Row", children: ["chip1", "chip2", "chip3"] },
          ...["Resource 1", "Resource 2", "decider"].map((label, i) => ({
            id: `chip${i + 1}`,
            component: "Chip",
            label,
          })),
          {
            id: "fields",
            component: "KeyValue",
            pairs: [
              { label: "Offers", value: "2 open · 1 matched" },
              { label: "Agreed share", value: "1 of 3" },
              { label: "Key", value: "ed25519 · 7f3a…c21" },
            ],
          },
          { id: "actions", component: "Row", children: ["message", "offers"] },
          button("message", "Message"),
          button("offers", "See offers", "ghost"),
        ]}
      />
    </>
  ),
  20: () => (
    <One
      component="Menu"
      props={{
        items: [
          { id: "edit", label: "Edit offer", icon: "edit", shortcut: "E" },
          { id: "copy", label: "Duplicate", icon: "copy", shortcut: "⌘D" },
          {
            id: "scope",
            label: "Change who sees it",
            icon: "lock",
            submenu: [
              { id: "coalition", label: "Coalition" },
              { id: "private", label: "Private" },
            ],
          },
          { id: "link", label: "Copy link to log entry", icon: "link" },
          {
            id: "withdraw",
            label: "Withdraw offer",
            icon: "trash",
            tone: "danger",
            shortcut: "⌫",
          },
        ],
      }}
    />
  ),
  21: () => (
    <Drawn
      components={[
        {
          id: "root",
          component: "Modal",
          title: "Leave the coalition?",
          open: { path: "/open" },
          dismissible: true,
          children: ["copy", "actions"],
        },
        text(
          "copy",
          "Your offers are withdrawn and the two tasks you hold go back to planning. The log keeps what you already signed. You can't rejoin this coalition.",
        ),
        { id: "actions", component: "Row", children: ["stay", "leave"] },
        button("stay", "Stay"),
        button("leave", "Leave", "ink"),
      ]}
      data={{ open: true }}
    />
  ),
  22: () => (
    <div className="phone" style={{ height: 372, alignSelf: "center" }}>
      <div className="phone-bar">
        <span>22:04</span>
        <span>5G</span>
      </div>
      <div className="col" style={{ flex: 1, padding: "8px 12px", background: "var(--canvas)" }}>
        <Drawn
          components={[
            {
              id: "root",
              component: "Card",
              title: "Resource for the task",
              children: ["copy"],
            },
            text("copy", "3 units · starts 22:30"),
          ]}
        />
        <Drawn
          components={[
            { id: "root", component: "Card", title: "Reserve for 07:10", children: ["copy"] },
            text("copy", "2 units held"),
          ]}
        />
      </div>
      <Drawn
        data={{ open: true }}
        components={[
          {
            id: "root",
            component: "Sheet",
            title: "Share the resource?",
            open: { path: "/open" },
            dismissible: true,
            children: ["copy", "join", "cancel"],
          },
          text("copy", "Your part is about €14. The others see you're joining, not your place."),
          button("join", "Join the task", "primary", "lg"),
          button("cancel", "Not this time", "ghost"),
        ]}
      />
    </div>
  ),
  23: () => (
    <div
      className="stage stage-dots"
      style={{ padding: 0, flexDirection: "row", height: 300, overflow: "hidden" }}
    >
      <div className="col" style={{ flex: 1, padding: 10 }}>
        <One component="Card" props={{ title: "Plan A" }} />
        <One component="Card" props={{ title: "Plan B" }} />
      </div>
      <div style={{ width: "74%", height: "100%" }}>
        <Drawn
          components={[
            {
              id: "root",
              component: "Drawer",
              title: "Offer details",
              width: bound(360),
              side: "right",
              body: ["fields", "divider", "question"],
              footer: ["actions"],
            },
            {
              id: "fields",
              component: "KeyValue",
              pairs: [
                { label: "From", value: "Member C" },
                { label: "What", value: "Resource run, 2D" },
                { label: "When", value: "after the review" },
                { label: "Seen by", value: "", scope: "task:t4" },
              ],
            },
            { id: "divider", component: "Divider" },
            {
              id: "question",
              component: "TextArea",
              label: "Ask before accepting",
              value: { path: "/question" },
            },
            { id: "actions", component: "Row", children: ["accept", "ask"] },
            button("accept", "Accept offer", "primary"),
            button("ask", "Ask"),
          ]}
          data={{ question: "Which size?" }}
        />
      </div>
    </div>
  ),
  24: () => (
    <>
      <One
        component="Toast"
        props={{ tone: "done", text: "You joined the task", undoWindow: bound(9) }}
      />
      <One
        component="Toast"
        props={{
          tone: "change",
          text: "Member B changed the task date",
          action: { label: "Show" },
        }}
      />
      <One
        component="Toast"
        props={{
          tone: "error",
          text: "Couldn't send. You're offline.",
          action: { label: "Retry" },
        }}
      />
    </>
  ),
};
