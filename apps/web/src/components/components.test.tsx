// SPDX-License-Identifier: Apache-2.0
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { bound, m1, m2, m3, planA, planB, planC } from "../gallery/fixtures";
import { StageBar } from "../shell/bars";
import { AgentDock, ConsentTray, WiringDrawer } from "../shell/dock";
import { ConsentCard, VoteTally } from "./consent";
import { Banner, EmptyState, ErrorState, Skeleton, Toast } from "./feedback";
import { ActivityStream, ChangedValue, LogStream, RippleBanner } from "./live";
import { PlanCompare, TensionCard } from "./plans";
import { Avatar, AvatarStack, Badge, Button, Card, ScopeBadge, Tag } from "./primitives";
import { NeedCard, OfferCard, TaskCard, Timeline } from "./work";

describe("Button", () => {
  it("fires on click and on keyboard", async () => {
    const onClick = vi.fn();
    render(<Button label="Accept" variant="primary" onClick={onClick} />);
    await userEvent.click(screen.getByRole("button", { name: "Accept" }));
    screen.getByRole("button", { name: "Accept" }).focus();
    await userEvent.keyboard("{Enter}");
    expect(onClick).toHaveBeenCalledTimes(2);
  });
  it("is inert when disabled", async () => {
    const onClick = vi.fn();
    render(<Button label="Accept" disabled onClick={onClick} />);
    await userEvent.click(screen.getByRole("button", { name: "Accept" }));
    expect(onClick).not.toHaveBeenCalled();
    expect(screen.getByRole("button")).toBeDisabled();
  });
  it("marks busy and ignores clicks while busy", async () => {
    const onClick = vi.fn();
    render(<Button label="Sending" busy onClick={onClick} />);
    const b = screen.getByRole("button", { name: "Sending" });
    expect(b).toHaveAttribute("aria-busy", "true");
    await userEvent.click(b);
    expect(onClick).not.toHaveBeenCalled();
  });
  it("draws the variant and forced states as classes", () => {
    const { rerender } = render(<Button label="A" variant="ink" />);
    expect(screen.getByRole("button")).toHaveClass("btn-ink");
    rerender(<Button label="A" variant="primary" forceState="hover" />);
    expect(screen.getByRole("button")).toHaveClass("btn-primary", "btn-hover");
    rerender(<Button label="A" size="lg" />);
    expect(screen.getByRole("button")).toHaveClass("btn-lg");
  });
});

describe("Tag, Badge, ScopeBadge, Avatar", () => {
  it("says status in words", () => {
    render(
      <>
        <Tag kind="needs" />
        <Tag kind="blocked" />
      </>,
    );
    expect(screen.getByText("Needs you")).toHaveClass("t-needs");
    expect(screen.getByText("Blocked")).toHaveClass("t-blocked");
  });
  it("badge carries its kind", () => {
    render(<Badge kind="vault" label="Vault answer" />);
    expect(screen.getByText("Vault answer")).toHaveClass("b-vault");
  });
  it("scope badge names the audience and the redaction", () => {
    render(<ScopeBadge audience="coalition" redact={["payload.cost"]} />);
    expect(screen.getByTitle(/Audience/)).toHaveTextContent("coalition − payload.cost");
  });
  it("avatar has an accessible name with presence", () => {
    render(<Avatar seat={2} label="Member 2" presence="away" />);
    expect(screen.getByRole("img", { name: "Member 2, away" })).toBeInTheDocument();
  });
  it("avatar stack counts the hidden ones", () => {
    render(<AvatarStack people={[m1, m2, m3]} max={2} />);
    expect(screen.getByRole("img", { name: "1 more" })).toBeInTheDocument();
  });
  it("a titled card is a named group", () => {
    render(<Card title="Card 1" tone="ask" />);
    expect(screen.getByRole("group", { name: "Card 1" })).toHaveClass("card-ask");
  });
});

describe("feedback", () => {
  it("banner blocked is an alert, info is status", () => {
    const { rerender } = render(<Banner tone="blocked" title="Blocked." />);
    expect(screen.getByRole("alert")).toHaveClass("bn-bad");
    rerender(<Banner tone="info" title="Info." />);
    expect(screen.getByRole("status")).toHaveClass("bn-info");
  });
  it("banner action and dismiss work by keyboard", async () => {
    const a = vi.fn();
    const d = vi.fn();
    render(<Banner tone="ask" title="T" action="Read" onAction={a} onDismiss={d} />);
    screen.getByRole("button", { name: "Read" }).focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(a).toHaveBeenCalled();
    expect(d).toHaveBeenCalled();
  });
  it("toast clips text to 60 and counts the undo window", async () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    render(<Toast tone="done" text={"x".repeat(80)} undoWindow={2} onDismiss={onDismiss} />);
    expect(screen.getByRole("status").textContent).toContain("…");
    expect(screen.getByRole("button", { name: /Undo/ })).toHaveTextContent("2 s");
    await vi.advanceTimersByTimeAsync(2100);
    expect(onDismiss).toHaveBeenCalled();
    vi.useRealTimers();
  });
  it("error toast is an alert", () => {
    render(<Toast tone="error" text="Could not send" action="Retry" />);
    expect(screen.getByRole("alert")).toHaveClass("toast-light");
  });
  it("empty state names what fills it", () => {
    render(<EmptyState title="No offers yet" body="Your agent is listening." action="Add" />);
    expect(screen.getByRole("region", { name: "No offers yet" })).toBeInTheDocument();
  });
  it("error state retries and shows details on request", async () => {
    const retry = vi.fn();
    render(<ErrorState cause="Cannot reach" details={{ code: "c1", ref: "r1" }} onRetry={retry} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Try again/ }));
    expect(retry).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Details" }));
    expect(screen.getByText(/c1/)).toBeInTheDocument();
  });
  it("reconnecting shows the missed count", () => {
    render(<ErrorState state="reconnecting" cause="" missed={3} />);
    expect(screen.getByRole("status")).toHaveTextContent("3 missed events");
  });
  it("skeleton is busy until filled, then shows the change", () => {
    const { rerender } = render(<Skeleton shape="card" label="Loading card" />);
    expect(screen.getByRole("status", { name: "Loading card" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    rerender(<Skeleton state="changed" value="New 1" previous="Old 1" />);
    expect(screen.getByText("Old 1")).toHaveStyle({ textDecoration: "line-through" });
    expect(screen.getByText("New 1")).toHaveClass("flash");
  });
});

describe("work cards", () => {
  it("task card shows the status in words for every status", () => {
    for (const s of [
      "open",
      "negotiating",
      "proposed",
      "decided",
      "committed",
      "done",
      "withdrawn",
    ] as const) {
      const { unmount } = render(<TaskCard taskId="t1" title="Task 1" status={s} />);
      expect(screen.getByRole("article", { name: `Task Task 1, ${s}` })).toBeInTheDocument();
      unmount();
    }
  });
  it("task card shows dependencies and lets a committed task be marked done", async () => {
    const done = vi.fn();
    render(
      <TaskCard
        taskId="t1"
        title="Task 1"
        status="committed"
        waitsFor={["t2"]}
        unblocks={["t4"]}
        onDone={done}
      />,
    );
    expect(screen.getByText(/waits for t2/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Mark done" }));
    expect(done).toHaveBeenCalled();
  });
  it("need card states", () => {
    const { rerender } = render(
      <NeedCard needId="n1" owner={m1} text="Need 1" state="matched" offers={2} />,
    );
    expect(screen.getByRole("article")).toHaveClass("card-live");
    rerender(<NeedCard needId="n1" owner={m1} text="Need 1" state="withdrawn" />);
    expect(screen.getByText("Need 1")).toHaveStyle({ textDecoration: "line-through" });
    rerender(
      <NeedCard needId="n1" owner={m1} text="Need 1" state="fulfilled" meta="by Member 2" />,
    );
    expect(screen.getByText("Agreed")).toBeInTheDocument();
  });
  it("offer card asks and emits", async () => {
    const accept = vi.fn();
    render(
      <OfferCard
        offerId="o1"
        what="Offer 1"
        state="open"
        needsYou
        cost={{ amount: bound(12), unit: "min" }}
        onAccept={accept}
      />,
    );
    expect(screen.getByText("Needs you")).toBeInTheDocument();
    expect(screen.getByText("12 min")).toHaveAttribute("title", "from event e12");
    await userEvent.click(screen.getByRole("button", { name: "Accept" }));
    expect(accept).toHaveBeenCalled();
  });
  it("offer card dead states are muted", () => {
    render(<OfferCard offerId="o1" what="Offer 1" state="expired" expires="09:00" />);
    expect(screen.getByRole("article")).toHaveStyle({ opacity: "0.55" });
  });
  it("timeline marks the current step", () => {
    render(
      <Timeline
        items={[
          { when: "Day 1", title: "Step 1", state: "done" },
          { when: "Day 2", title: "Step 2", state: "now" },
        ]}
      />,
    );
    const items = within(screen.getByRole("list", { name: "Timeline" })).getAllByRole("listitem");
    expect(items[1]).toHaveAttribute("aria-current", "step");
    expect(items[0]).not.toHaveAttribute("aria-current");
  });
});

describe("plans and consent", () => {
  it("plan compare accepts a plan and shows why one was rejected", async () => {
    const decide = vi.fn();
    render(
      <PlanCompare
        plans={[planA, planB]}
        rejected={[{ plan: planC, reason: "Breaks a rule" }]}
        onDecide={decide}
      />,
    );
    expect(screen.getByText("Breaks a rule")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Accept A" }));
    expect(decide).toHaveBeenCalledWith("p1");
  });
  it("plan compare is locked once decided or superseded", () => {
    render(<PlanCompare plans={[planA, planB]} state="decided" decidedId="p1" />);
    expect(screen.getByRole("button", { name: "Accepted" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Accept B" })).toBeDisabled();
  });
  const options = [
    { id: "o1", label: "Option 1", tradeoffs: ["faster"] },
    { id: "o2", label: "Option 2", tradeoffs: ["cheaper"] },
  ];
  const deciders = [{ ...m1, answered: true }, { ...m2 }];
  it("tension card chooses with the keyboard", async () => {
    const choose = vi.fn();
    render(
      <TensionCard
        title="Pick one"
        options={options}
        deciders={deciders}
        answered={1}
        onChoose={choose}
      />,
    );
    const radios = screen.getAllByRole("radio");
    radios[0]?.focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(radios[1]).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Choose Option 2" }));
    expect(choose).toHaveBeenCalledWith("o2");
    expect(screen.getByText("1 of 2 answered")).toBeInTheDocument();
  });
  it("tension card is read only once decided", () => {
    render(
      <TensionCard
        title="Pick one"
        options={options}
        deciders={deciders}
        answered={2}
        state="decided"
        chosenId="o2"
      />,
    );
    for (const r of screen.getAllByRole("radio")) expect(r).toBeDisabled();
    expect(screen.queryByRole("button", { name: /Choose/ })).toBeNull();
  });
  const subject = { kind: "plan", id: "p1", revision: 2 };
  it("consent card sends yes and no with its subject", async () => {
    const decide = vi.fn();
    render(
      <ConsentCard
        subject={subject}
        title="Plan A"
        yesLabel="Accept Plan A"
        noLabel="Not this plan"
        onDecide={decide}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Accept Plan A" }));
    await userEvent.click(screen.getByRole("button", { name: "Not this plan" }));
    expect(decide).toHaveBeenNthCalledWith(1, true, subject);
    expect(decide).toHaveBeenNthCalledWith(2, false, subject);
    expect(screen.getByText(/revision 2/)).toBeInTheDocument();
  });
  it("consent card stale, answered, expired and busy", () => {
    const { rerender } = render(
      <ConsentCard subject={subject} title="P" state="stale" currentRevision={3} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("revision 3");
    expect(screen.queryByRole("button", { name: "Accept" })).toBeNull();
    rerender(<ConsentCard subject={subject} title="P" state="answered" answer />);
    expect(screen.getByText("You said yes")).toBeInTheDocument();
    rerender(<ConsentCard subject={subject} title="P" state="expired" />);
    expect(screen.getByText("deadline passed")).toBeInTheDocument();
    rerender(<ConsentCard subject={subject} title="P" busy />);
    expect(screen.getByRole("button", { name: "Accept" })).toBeDisabled();
  });
  it("vote tally hides answers until closed", () => {
    const d = [
      { ...m1, answered: true, answer: true },
      { ...m2, answered: false },
    ];
    const { rerender } = render(<VoteTally title="Plan A" deciders={d} />);
    expect(screen.getByText(/waiting/, { selector: ".num" })).toHaveTextContent("1 answered");
    expect(screen.queryByText("Member 1 yes")).toBeNull();
    rerender(
      <VoteTally
        title="Plan A"
        closed
        outcome="split"
        deciders={[
          { ...m1, answered: true, answer: true },
          { ...m2, answered: true, answer: false },
        ]}
      />,
    );
    expect(screen.getByText("Member 1 yes")).toBeInTheDocument();
    expect(screen.getByText("Member 2 no")).toBeInTheDocument();
  });
});

describe("live", () => {
  it("ripple banner counts from the lists and opens", async () => {
    const open = vi.fn();
    render(
      <RippleBanner
        ripple={{
          by: "Member 2",
          change: "moved step 2",
          invalidated: ["a", "b"],
          untouched: ["c"],
        }}
        onOpen={open}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("2 of your 3 tasks changed; 1 stayed.");
    await userEvent.click(screen.getByRole("button", { name: "What changed" }));
    expect(open).toHaveBeenCalled();
  });
  it("changed value goes flash, then tinted after 900 ms", async () => {
    vi.useFakeTimers();
    try {
      render(<ChangedValue before="16:00" after="17:00" />);
      expect(screen.getByText("17:00")).toHaveClass("flash");
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });
      expect(screen.getByText("17:00")).toHaveClass("seen");
    } finally {
      vi.useRealTimers();
    }
  });
  it("changed value is marked seen when the viewer looks", async () => {
    render(<ChangedValue before="16:00" after="17:00" />);
    await userEvent.hover(screen.getByText("17:00"));
    expect(screen.getByText("17:00")).not.toHaveClass("flash");
    expect(screen.getByText("17:00")).not.toHaveClass("seen");
  });
  it("changed value fixed states for the gallery", () => {
    render(<ChangedValue after="x" state="tinted" />);
    expect(screen.getByText("x")).toHaveClass("seen");
  });
  it("activity stream filters and opens an entry", async () => {
    const open = vi.fn();
    render(
      <ActivityStream
        onOpen={open}
        items={[
          { seq: 1, actor: m1, verb: "accepted", object: "Plan A", time: "1 m", decision: true },
          { seq: 2, actor: m2, verb: "changed", object: "t2", time: "now", aboutMe: true },
        ]}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Decisions" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: /accepted/ }));
    expect(open).toHaveBeenCalledWith(1);
    expect(screen.getByRole("button", { name: "Decisions" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
  it("log stream never hides a gap and marks receipt-only rows", async () => {
    const open = vi.fn();
    render(
      <LogStream
        onOpen={open}
        entries={[
          { seq: 1, ts: "t", type: "coalition.need", summary: "s1", hash: "aa", form: "original" },
          {
            seq: 4,
            ts: "t",
            type: "coalition.decide",
            summary: "",
            hash: "bb",
            form: "receipt-only",
          },
        ]}
      />,
    );
    expect(screen.getByText(/gap: #2/)).toHaveTextContent("#2–#3");
    expect(screen.getByText("· not for you ·")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /s1/ }));
    expect(open).toHaveBeenCalledWith(1);
  });
  it("log stream says when the chain is broken", () => {
    render(<LogStream entries={[]} chainOk={false} />);
    expect(screen.getByText("chain broken")).toBeInTheDocument();
  });
});

describe("shell parts", () => {
  it("stage bar marks done, current and next in words", () => {
    render(<StageBar current="Decide" />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(7);
    expect(screen.getByText(/Decide/, { selector: "span.sg" })).toHaveAttribute(
      "data-state",
      "now",
    );
    expect(screen.getByText(/Gather/, { selector: "span.sg" })).toHaveAttribute(
      "data-state",
      "done",
    );
    expect(screen.getByText(/Live/, { selector: "span.sg" })).toHaveAttribute("data-state", "next");
    expect(items.filter((i) => i.getAttribute("aria-current") === "step")).toHaveLength(1);
  });
  it("compact stage bar shows only the current stage", () => {
    render(<StageBar current="Act" compact />);
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });
  it("consent tray empty, one and many", async () => {
    const open = vi.fn();
    const { rerender } = render(<ConsentTray requests={[]} />);
    expect(screen.getByText("Nothing waits for you.")).toBeInTheDocument();
    rerender(
      <ConsentTray requests={[{ id: "r1", kind: "plan", title: "Plan A" }]} onOpen={open} />,
    );
    expect(screen.getByText("1 decision waits for you")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Decide" }));
    expect(open).toHaveBeenCalledWith("r1");
    rerender(
      <ConsentTray
        onOpen={open}
        requests={[
          { id: "r1", kind: "plan", title: "Plan A", urgent: true },
          { id: "r2", kind: "charter", title: "Rev 3" },
        ]}
      />,
    );
    expect(screen.getByRole("region", { name: "Decisions waiting for you" })).toHaveAttribute(
      "data-state",
      "urgent",
    );
    await userEvent.click(screen.getByRole("button", { name: "Open Rev 3" }));
    expect(open).toHaveBeenLastCalledWith("r2");
  });
  it("agent dock sends a message and explains a disabled composer", async () => {
    const say = vi.fn();
    const { rerender } = render(<AgentDock messages={[]} onSay={say} />);
    await userEvent.type(screen.getByLabelText("Ask your agent"), "hello 1{Enter}");
    expect(say).toHaveBeenCalledWith("hello 1");
    rerender(<AgentDock messages={[]} composerDisabledReason="Not connected." />);
    expect(screen.getByLabelText("Ask your agent")).toBeDisabled();
    expect(screen.getByText("Not connected.")).toBeInTheDocument();
    rerender(<AgentDock messages={[]} state="offline" />);
    expect(screen.getByLabelText("Ask your agent")).toBeDisabled();
  });
  it("agent dock states: streaming and tool-call", () => {
    const { rerender } = render(
      <AgentDock messages={[{ id: "1", from: "agent", text: "Hi" }]} state="streaming" />,
    );
    expect(screen.getAllByRole("status")[0]).toHaveTextContent("writing");
    rerender(<AgentDock messages={[]} state="tool-call" />);
    expect(screen.getAllByRole("status")[0]).toHaveTextContent("checking your vault");
  });
  it("wiring drawer states", () => {
    const { rerender } = render(<WiringDrawer state="closed" message={{ a: 1 }} />);
    expect(screen.queryByRole("complementary")).toBeNull();
    rerender(<WiringDrawer state="inspecting" message={{ type: "x" }} onVerify={() => {}} />);
    expect(screen.getByRole("complementary")).toHaveAttribute("data-state", "inspecting");
    rerender(<WiringDrawer state="verified" message={{ type: "x" }} />);
    expect(screen.getByText("Verified")).toBeInTheDocument();
    rerender(<WiringDrawer state="broken" message={{ type: "x" }} />);
    expect(screen.getByText("Chain broken")).toBeInTheDocument();
  });
});
