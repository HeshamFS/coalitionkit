// SPDX-License-Identifier: Apache-2.0
export const examples: Record<string, { state: string; props: Record<string, unknown> }[]> = {
  MapView: [
    {
      state: "default",
      props: {
        points: [
          {
            id: "place1",
            label: "Place 1",
            kind: "origin",
            lat: { value: 70, event_ref: "example:1" },
            lng: { value: 120, event_ref: "example:1" },
          },
          {
            id: "place2",
            label: "Place 2",
            ref: "Plan A · 3 rooms",
            kind: "place",
            lat: { value: 74, event_ref: "example:1" },
            lng: { value: 372, event_ref: "example:1" },
          },
          {
            id: "place3",
            label: "Place 3",
            kind: "place",
            lat: { value: 160, event_ref: "example:1" },
            lng: { value: 470, event_ref: "example:1" },
          },
          {
            id: "place4",
            label: "Place 4",
            kind: "place",
            lat: { value: 60, event_ref: "example:1" },
            lng: { value: 260, event_ref: "example:1" },
          },
        ],
        routes: [
          {
            path: [
              {
                x: { value: 120, event_ref: "example:1" },
                y: { value: 70, event_ref: "example:1" },
              },
              {
                control1: {
                  x: { value: 160, event_ref: "example:1" },
                  y: { value: 90, event_ref: "example:1" },
                },
                control2: {
                  x: { value: 190, event_ref: "example:1" },
                  y: { value: 120, event_ref: "example:1" },
                },
                x: { value: 230, event_ref: "example:1" },
                y: { value: 140, event_ref: "example:1" },
              },
              {
                control1: {
                  x: { value: 270, event_ref: "example:1" },
                  y: { value: 160, event_ref: "example:1" },
                },
                control2: {
                  x: { value: 330, event_ref: "example:1" },
                  y: { value: 170, event_ref: "example:1" },
                },
                x: { value: 372, event_ref: "example:1" },
                y: { value: 74, event_ref: "example:1" },
              },
            ],
            mode: "Route 1",
            eta: "22:58",
          },
        ],
        areas: [
          {
            label: "Within 12 min",
            polygon: [
              {
                x: { value: 330, event_ref: "example:1" },
                y: { value: 30, event_ref: "example:1" },
              },
              {
                x: { value: 410, event_ref: "example:1" },
                y: { value: 34, event_ref: "example:1" },
              },
              {
                x: { value: 404, event_ref: "example:1" },
                y: { value: 110, event_ref: "example:1" },
              },
              {
                x: { value: 326, event_ref: "example:1" },
                y: { value: 104, event_ref: "example:1" },
              },
            ],
          },
        ],
        you: {
          position: {
            lng: { value: 170, event_ref: "example:1" },
            lat: { value: 96, event_ref: "example:1" },
          },
          precision: "approximate",
          accuracy: { value: 80, event_ref: "example:1" },
        },
        selected: "place2",
      },
    },
  ],
  IndoorMap: [
    {
      state: "default",
      props: {
        plan: "venue1",
        rooms: [
          { id: "room1", label: "Room 1" },
          { id: "room2", label: "Room 2" },
          { id: "room3", label: "Room 3", selected: true },
          { id: "room4", label: "Room 4" },
          {
            id: "room5",
            label: "Service desk",
            x: { value: 24, event_ref: "example:1" },
            y: { value: 110, event_ref: "example:1" },
            width: { value: 80, event_ref: "example:1" },
            height: { value: 44, event_ref: "example:1" },
          },
          {
            id: "queue",
            label: "Queue · 40 min",
            kind: "queue",
            x: { value: 190, event_ref: "example:1" },
            y: { value: 110, event_ref: "example:1" },
            width: { value: 88, event_ref: "example:1" },
            height: { value: 44, event_ref: "example:1" },
          },
          {
            id: "exit",
            label: "Exit 3",
            kind: "exit",
            x: { value: 112, event_ref: "example:1" },
            y: { value: 226, event_ref: "example:1" },
            width: { value: 56, event_ref: "example:1" },
            height: { value: 18, event_ref: "example:1" },
          },
        ],
        you: {
          x: { value: 190, event_ref: "example:1" },
          y: { value: 82, event_ref: "example:1" },
        },
        path: [
          { x: { value: 190, event_ref: "example:1" }, y: { value: 72, event_ref: "example:1" } },
          { x: { value: 190, event_ref: "example:1" }, y: { value: 92, event_ref: "example:1" } },
          { x: { value: 60, event_ref: "example:1" }, y: { value: 92, event_ref: "example:1" } },
          { x: { value: 60, event_ref: "example:1" }, y: { value: 196, event_ref: "example:1" } },
          { x: { value: 140, event_ref: "example:1" }, y: { value: 196, event_ref: "example:1" } },
          { x: { value: 140, event_ref: "example:1" }, y: { value: 232, event_ref: "example:1" } },
        ],
        liveLayers: [
          {
            label: "to exit 3 · step-free",
            value: { value: 6, event_ref: "example:1" },
            source: "live queue",
          },
        ],
      },
    },
  ],
  RouteCard: [
    {
      state: "default",
      props: {
        mode: "Route to Place 1",
        costPerMember: { value: 14, event_ref: "example:1" },
        currency: "EUR",
        eta: "22:58",
        distance: { value: 7400, event_ref: "example:1" },
        progress: { value: 0.35, event_ref: "example:1" },
        participants: ["Member A", "Member B", "Member C"],
        steps: [
          { label: "Place 3", state: "done", time: "22:45" },
          { label: "Route 1", state: "now", time: "now" },
          { label: "Place 1", state: "next", time: "22:58" },
        ],
      },
    },
  ],
  PlacePicker: [
    {
      state: "default",
      props: {
        query: "Place",
        results: [
          {
            place: "Place 1",
            distance: { value: 0.6, event_ref: "example:1" },
            facts: ["Available 24 h"],
            limitCheck: "within your limit",
          },
          {
            place: "Place 2",
            distance: { value: 14, event_ref: "example:1" },
            facts: ["Available until 01:00"],
            limitCheck: "over your limit",
          },
          {
            place: "Place 3",
            facts: ["in Place 1", "unavailable"],
            limitCheck: "no limit asked",
          },
        ],
        pin: { ref: "Place 1" },
      },
    },
  ],
  LocationShare: [
    {
      state: "default",
      props: { audience: "Task 1 (A, B, C)", precision: "approximate", until: "arrival" },
    },
  ],
  ArrivalCard: [
    {
      state: "default",
      props: {
        place: "Place 1",
        arrivedAt: "22:58",
        next: "Room 2 of 3 is yours. Use the coalition booking.",
        others: [
          { participant: "Member B", state: "arrived", arrivedAt: "22:58" },
          { participant: "Member C", state: "is 4 min away" },
        ],
      },
    },
  ],
  CalendarWeek: [
    {
      state: "default",
      props: {
        range: { start: "2031-06-03" },
        events: [
          {
            kind: "task",
            task: "Task 1 ✓",
            state: "done",
            start: "2031-06-03T17:00:00Z",
            end: "2031-06-03T18:45:00Z",
            assignee: "Member A",
          },
          {
            kind: "private-busy",
            start: "2031-06-03T10:45:00Z",
            end: "2031-06-03T13:20:00Z",
            assignee: "Member A",
          },
          {
            kind: "task",
            task: "Task 2 · 16:00",
            state: "scheduled",
            start: "2031-06-04T15:00:00Z",
            end: "2031-06-04T16:45:00Z",
            assignee: "Member B",
          },
          {
            kind: "task",
            task: "Task 3",
            state: "active",
            now: "2031-06-05T11:35:00Z",
            start: "2031-06-05T09:07:00Z",
            end: "2031-06-05T12:03:00Z",
            assignee: "Member A",
          },
          {
            kind: "deadline",
            task: "decide Plan A by 12:00",
            start: "2031-06-05T13:00:00Z",
            end: "2031-06-05T14:45:00Z",
            assignee: "Member A",
          },
          {
            kind: "task",
            task: "Task 5 · 14:00",
            state: "scheduled",
            start: "2031-06-06T15:00:00Z",
            end: "2031-06-06T17:35:00Z",
            assignee: "Member B",
          },
          {
            kind: "private-busy",
            start: "2031-06-06T09:35:00Z",
            end: "2031-06-06T11:20:00Z",
            assignee: "Member A",
          },
          {
            kind: "task",
            task: "Task 6 (C) · weekend",
            state: "weekend",
            start: "2031-06-07T10:45:00Z",
            end: "2031-06-07T18:45:00Z",
            assignee: "Member C",
          },
        ],
      },
    },
  ],
  TimeZoneStrip: [
    {
      state: "default",
      props: {
        now: "2030-06-05T09:20:00Z",
        people: [
          {
            participant: "Member A",
            tz: "Europe/Berlin",
            workingHours: [
              {
                start: { value: 8, event_ref: "example:1" },
                end: { value: 18, event_ref: "example:1" },
              },
            ],
          },
          {
            participant: "Member B",
            tz: "Europe/London",
            workingHours: [
              {
                start: { value: 6, event_ref: "example:1" },
                end: { value: 16, event_ref: "example:1" },
              },
            ],
          },
          {
            participant: "Member C",
            tz: "Australia/Sydney",
            workingHours: [
              {
                start: { value: 1, event_ref: "example:1" },
                end: { value: 10, event_ref: "example:1" },
              },
            ],
          },
        ],
      },
    },
  ],
  AgendaList: [
    {
      state: "default",
      props: {
        day: "2030-06-05",
        items: [
          { time: "09:00", title: "Task 3 \u00b7 Member A", state: "agreed" },
          { time: "12:00", title: "Decide Plan A", state: "needs-you" },
          { time: "12:30", title: "Task 4 \u00b7 Member B", state: "next" },
          { time: "16:00", title: "Member sync call", state: "next", action: "Join" },
        ],
      },
    },
  ],
};
