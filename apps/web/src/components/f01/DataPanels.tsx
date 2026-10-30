// SPDX-License-Identifier: Apache-2.0
import { One } from "../../gallery/Drawn";
export function ListPanel() {
  return (
    <One
      component="List"
      props={{ items: { path: "/items" } }}
      data={{
        items: [
          {
            id: "p1",
            leading: { seat: 1 },
            title: "Member A",
            meta: "offered a resource unit",
            trailing: "2 m",
          },
          {
            id: "p2",
            leading: { seat: 2 },
            title: "Member B",
            meta: "needs a resource before 01:00",
            trailing: "live",
          },
          {
            id: "host",
            leading: { seat: "host" },
            title: "Host",
            meta: "signed receipt #41",
            trailing: "5 m",
          },
        ],
      }}
    />
  );
}
export function CommandPanel() {
  return (
    <One
      component="CommandPalette"
      props={{ query: { path: "/query" }, groups: "actions" }}
      data={{
        query: {
          text: "prop  ",
          groups: [
            {
              label: "Actions",
              items: [
                {
                  id: "plan",
                  label: "Propose the plan on the canvas",
                  icon: "send",
                  shortcut: "↵",
                },
                { id: "new", label: "New proposal from these 3 offers", icon: "plus" },
              ],
            },
            {
              label: "In this coalition",
              items: [
                { id: "p2", label: "Plan B · proposed 21:47", icon: "square", hint: "plan" },
                { id: "l42", label: "Log #42 · coalition.propose", icon: "list", hint: "log" },
              ],
            },
          ],
        },
      }}
    />
  );
}
export function TablePanel() {
  return (
    <One
      component="Table"
      props={{
        sortable: true,
        selection: "many",
        selected: ["o1"],
        page: { value: 1, event_ref: "example" },
        pageSize: { value: 4, event_ref: "example" },
        total: { value: 12, event_ref: "example" },
        action: { label: "Add to plan" },
        rows: { path: "/rows" },
        columns: [
          { key: "offer", label: "Offer", sortable: false },
          { key: "from", label: "From", format: "avatar", sortable: false },
          { key: "when", label: "When", direction: "desc" },
          { key: "scope", label: "Scope", format: "scope", sortable: false },
          { key: "status", label: "Status", format: "status", sortable: false },
          { key: "cost", label: "Cost", align: "right", sortable: false },
        ],
      }}
      data={{
        rows: [
          {
            id: "o1",
            offer: "Resource, 3 units",
            from: { label: "Member A", seat: 1 },
            when: "22:30",
            scope: "coalition",
            status: "Agreed",
            cost: "≈ €42",
          },
          {
            id: "o2",
            offer: "Resource, 2 units",
            from: { label: "Member B", seat: 2 },
            when: "22:10",
            scope: "task:t2",
            status: "Needs you",
            cost: "[vault]",
          },
          {
            id: "o3",
            offer: "Unit at 07:10",
            from: { label: "Member C", seat: 3 },
            when: "21:58",
            scope: "coalition",
            status: "Changed",
            cost: "€0",
          },
          {
            id: "o4",
            offer: "Resource access",
            from: { label: "Member A", seat: 1 },
            when: "21:40",
            scope: "private",
            status: "Private",
            cost: { redacted: true },
          },
        ],
      }}
    />
  );
}
