// SPDX-License-Identifier: Apache-2.0
export const examples: Record<string, { state: string; props: Record<string, unknown> }[]> = {
  CoalitionHeader: [
    {
      state: "default",
      props: {
        title: "The three-member coalition",
        goal: "Complete the shared goal across three members by Monday.",
        pack: "Shared resources",
        revision: { value: 2, event_ref: "example:1" },
        yourState: "needs-you",
        budget: {
          used: { value: 0.71, event_ref: "example:1" },
          cap: { value: 3, event_ref: "example:1" },
        },
        counts: {
          people: { value: 3, event_ref: "example:1" },
          agents: { value: 5, event_ref: "example:1" },
          watchers: { value: 1, event_ref: "example:1" },
          tasks: { value: 6, event_ref: "example:1" },
          plans: { value: 2, event_ref: "example:1" },
        },
      },
    },
  ],
  StageTrack: [
    {
      state: "default",
      props: {
        current: { path: "/current" },
        progress: { value: 2, event_ref: "example:1" },
        stages: [
          { id: "Germinate", label: "Germinate", state: "done" },
          { id: "Gather", label: "Gather", state: "done" },
          { id: "Negotiate", label: "Negotiate", state: "done" },
          { id: "Decide", label: "Decide", state: "now" },
          { id: "Act", label: "Act", state: "next" },
          { id: "Live", label: "Live", state: "next" },
          { id: "Dissolve", label: "Dissolve", state: "next" },
        ],
      },
    },
  ],
  SeatRing: [
    {
      state: "default",
      props: {
        goal: "by Mon",
        openSeats: { value: 2, event_ref: "example:1" },
        seats: [
          {
            participant: "Member A",
            seat: { value: 3, event_ref: "example:1" },
            role: "member",
            state: "owes",
          },
          {
            participant: "Member B",
            seat: { value: 1, event_ref: "example:1" },
            role: "member",
            state: "acting",
          },
          {
            participant: "Member C",
            seat: { value: 5, event_ref: "example:1" },
            role: "member",
            state: "idle",
          },
        ],
      },
    },
  ],
  CharterCard: [
    {
      state: "default",
      props: {
        revision: { value: 2, event_ref: "example:1" },
        rules: [
          {
            n: { value: 1, event_ref: "example:1" },
            text: "Every member decides each plan; 4 hours to answer",
          },
          {
            n: { value: 2, event_ref: "example:1" },
            text: "Raw data stays with its owner; only results are shared",
          },
          {
            n: { value: 3, event_ref: "example:1" },
            text: "No member carries more than half the hours",
          },
          {
            n: { value: 4, event_ref: "example:1" },
            text: "Agent budget \u20ac3 for the coalition",
          },
        ],
        roles: [{ name: "organizer" }, { name: "member" }, { name: "watcher" }],
        signedBy: ["p1", "p2", "p3"],
      },
    },
  ],
  ParticipantCard: [
    {
      state: "agreed",
      props: {
        participant: "Member A",
        seat: { value: 3, event_ref: "example:1" },
        roles: ["organizer", "decider"],
        capabilities: ["Resource 1", "Resource 2"],
        state: "agreed",
      },
    },
    {
      state: "acting",
      props: {
        participant: "Member A",
        seat: { value: 3, event_ref: "example:1" },
        roles: ["organizer", "decider"],
        capabilities: ["Resource 1", "Resource 2"],
        state: "acting",
      },
    },
    {
      state: "owes",
      props: {
        participant: "Member A",
        seat: { value: 3, event_ref: "example:1" },
        roles: ["organizer", "decider"],
        capabilities: ["Resource 1", "Resource 2"],
        state: "owes",
      },
    },
    {
      state: "watcher",
      props: {
        participant: "Member A",
        seat: { value: 3, event_ref: "example:1" },
        roles: ["organizer", "decider"],
        capabilities: ["Resource 1", "Resource 2"],
        state: "watcher",
      },
    },
    {
      state: "invited",
      props: {
        participant: "Member A",
        seat: { value: 3, event_ref: "example:1" },
        roles: ["organizer", "decider"],
        capabilities: ["Resource 1", "Resource 2"],
        state: "invited",
      },
    },
    {
      state: "left",
      props: {
        participant: "Member A",
        seat: { value: 3, event_ref: "example:1" },
        roles: ["organizer", "decider"],
        capabilities: ["Resource 1", "Resource 2"],
        state: "left",
      },
    },
  ],
  ActsForGraph: [
    {
      state: "default",
      props: {
        acting: "Agent B",
        people: [
          { participant: "Member A", ownerKid: "owner-A" },
          { participant: "Member B", ownerKid: "owner-B" },
          { participant: "Member C", ownerKid: "owner-C" },
        ],
        agents: [
          {
            card: "Agent A",
            cardKid: "card-A",
            vendor: "A2A",
            runtime: "member service",
            actsFor: "Member A",
          },
          {
            card: "Agent B",
            cardKid: "card-B",
            vendor: "A2A",
            runtime: "member service",
            actsFor: "Member B",
          },
          {
            card: "Agent C",
            cardKid: "card-C",
            vendor: "A2A",
            runtime: "member service",
            actsFor: "Member C",
          },
        ],
      },
    },
  ],
  VendorBadge: [
    { state: "A2A", props: { transport: "A2A", framework: "ADK" } },
    { state: "A2A", props: { transport: "A2A", framework: "LangGraph" } },
    { state: "MCP", props: { transport: "MCP", framework: "chat client" } },
    { state: "hosted", props: { transport: "hosted", framework: "Muse Spark" } },
    { state: "minted", props: { transport: "minted", framework: "Modal" } },
    { state: "local", props: { transport: "local", framework: "Glimmer" } },
  ],
  AgentPresence: [
    {
      state: "live",
      props: {
        agent: "Agent B",
        state: "live",
        latencyMs: { value: 140, event_ref: "example:1" },
        pinnedKid: "7f3a\u2026",
      },
    },
    {
      state: "idle",
      props: {
        agent: "Agent B",
        state: "idle",
        latencyMs: { value: 140, event_ref: "example:1" },
        pinnedKid: "7f3a\u2026",
      },
    },
    {
      state: "offline",
      props: {
        agent: "Agent B",
        state: "offline",
        latencyMs: { value: 140, event_ref: "example:1" },
        pinnedKid: "7f3a\u2026",
      },
    },
  ],
  RoleChip: [
    { state: "held", props: { role: "organizer", open: false } },
    { state: "member", props: { role: "member", open: false } },
    { state: "decider", props: { role: "decider", open: false } },
    { state: "watcher", props: { role: "watcher", open: false } },
    { state: "open", props: { role: "helper", open: true } },
  ],
  RoleMatrix: [
    {
      state: "default",
      props: {
        roles: ["organizer", "member", "watcher"],
        rights: [
          {
            action: "offer, need",
            rights: { organizer: "\u2713", member: "\u2713", watcher: "\u2013" },
          },
          {
            action: "decide plans",
            rights: { organizer: "\u2713", member: "\u2713", watcher: "\u2013" },
          },
          {
            action: "see results",
            rights: { organizer: "\u2713", member: "\u2713", watcher: "\u2713" },
          },
          {
            action: "see raw data",
            rights: { organizer: "own", member: "own", watcher: "\u2013" },
          },
          {
            action: "change charter",
            rights: { organizer: "propose", member: "accept", watcher: "\u2013" },
          },
        ],
      },
    },
  ],
  Roster: [
    {
      state: "default",
      props: {
        members: [
          {
            participant: "Member A",
            roles: ["member"],
            agents: { value: 1, event_ref: "example:1" },
            acceptedRevision: { value: 2, event_ref: "example:1" },
            load: { value: 14, event_ref: "example:1" },
            state: "agreed",
          },
          {
            participant: "Member B",
            roles: ["member"],
            agents: { value: 1, event_ref: "example:1" },
            acceptedRevision: { value: 2, event_ref: "example:1" },
            load: { value: 9, event_ref: "example:1" },
            state: "changed",
          },
          {
            participant: "Member C",
            roles: ["member"],
            agents: { value: 1, event_ref: "example:1" },
            acceptedRevision: { value: 1, event_ref: "example:1" },
            load: { value: 11, event_ref: "example:1" },
            state: "owes",
          },
        ],
      },
    },
  ],
  PackChip: [
    {
      state: "default",
      props: {
        pack: {
          id: "pack1",
          name: "Shared resources",
          version: "0.1",
          views: ["v1", "v2", "v3", "v4"],
          policies: ["allow", "redact"],
          authorKid: "0c11\u2026",
        },
      },
    },
  ],
  LeaveControl: [
    {
      state: "default",
      props: {
        consequences: [
          "2 of your tasks go back to planning",
          "Your 3 offers are withdrawn",
          "Your vault leaves with you",
        ],
      },
    },
  ],
  InviteList: [
    {
      state: "default",
      props: {
        invitations: [
          {
            participant: "Member E",
            role: "member",
            channel: "link",
            sentAt: "20:14",
            expires: "22 h",
            state: "invited",
          },
          { participant: "Member D", role: "watcher", state: "joined" },
        ],
        openSeats: ["member"],
      },
    },
  ],
};

examples.ParticipantCard?.forEach((example, index) => {
  example.props.participant = `Member ${String.fromCharCode(65 + index)}`;
  example.props.seat = { value: [3, 1, 5, 4, 2, 5][index], event_ref: "example:1" };
  if (example.state === "acting") {
    example.props.act = "answering query q12";
    example.props.roles = ["member", "decider"];
  }
  if (example.state === "owes") {
    example.props.roles = ["member", "decider"];
    example.props.capabilities = ["Resource 3"];
  }
  if (example.state === "watcher") {
    example.props.roles = ["observe only"];
    example.props.capabilities = [];
  }
  if (example.state === "invited") {
    example.props.roles = ["invited 2 h ago"];
    example.props.act = "hasn't joined · invite expires in 22 h";
  }
  if (example.state === "left") {
    example.props.roles = ["left yesterday"];
    example.props.act = "2 tasks went back to planning";
  }
});
