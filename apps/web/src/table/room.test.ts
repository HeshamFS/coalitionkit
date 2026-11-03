// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { answerAll, partRequests } from "./commit";
import { budgetCsv, exportsFor, listCsv, toIcs, toText } from "./exports";
import { layoutClass, momentIndex, sideFor } from "./phase";
import { lightsOf, readRoom } from "./room";
import { SCENES } from "./scenes";

describe("readRoom", () => {
  it("is null when the host sent no room, so the five-tab room stays", () => {
    expect(readRoom(null)).toBeNull();
    expect(readRoom({})).toBeNull();
    expect(readRoom({ room: "x" })).toBeNull();
    expect(readRoom({ room: [1] })).toBeNull();
  });

  it("never throws on malformed values and defaults them", () => {
    const room = readRoom({
      room: {
        phase: 7,
        lights: "purple",
        goal: { a: 1 },
        seats: [null, 3, { seat: "" }, { seat: "s1", kind: "alien", you: "yes" }],
        needs: "none",
        activity: [{ id: "a", verb: "dance", state: "sleeping", ms: "fast", seat: 4 }, { nope: 1 }],
        results: [{ id: "r", messages: "no", sources: [1, "e1"], tree: {} }],
        common: { slots: "x", compared: -4 },
        change: { moved: [1, "n1"], untouched: "3" },
        begin: { can: "true" },
        mine: {
          brief: [{ id: "q", status: "weird" }],
          tasks: [{ task_id: "t", can_mark_done: 1 }],
          for_you: { p: 3, q: "ok" },
        },
        checked: "many",
      },
    });
    expect(room).not.toBeNull();
    expect(room?.phase).toBe("gather");
    expect(room?.lights).toBe("day");
    expect(room?.goal).toBe("");
    expect(room?.seats).toEqual([
      { seat: "s1", role: "", label: "s1", kind: "person", you: false, signed: false, state: "" },
    ]);
    expect(room?.needs).toEqual([]);
    expect(room?.activity).toHaveLength(1);
    expect(room?.activity[0]).toMatchObject({
      verb: "reading",
      state: "done",
      ms: null,
      seat: null,
    });
    expect(room?.results[0]).toMatchObject({ messages: [], sources: ["e1"], tree: [] });
    expect(room?.common).toEqual({ slots: [], count_private: null, compared: 0 });
    expect(room?.change).toEqual({ text: "", from: null, moved: ["n1"], asked: [], untouched: 0 });
    expect(room?.begin).toEqual({ can: false, open_seats: 0 });
    expect(room?.mine.brief[0]?.status).toBe("open");
    expect(room?.mine.tasks[0]?.can_mark_done).toBe(false);
    expect(room?.mine.for_you).toEqual({ q: "ok" });
    expect(room?.checked).toBe(0);
  });

  it("reads every scripted scene back unchanged", () => {
    for (const s of SCENES) expect(readRoom({ room: s.room })).toEqual(s.room);
  });
});

describe("lights, phase, rail, layout", () => {
  it("the host's lights alone decide day or night", () => {
    const day = SCENES.find((s) => s.id === "arrive")?.room;
    const night = SCENES.find((s) => s.id === "work")?.room;
    if (!day || !night) throw new Error("scenes missing");
    expect(lightsOf(day)).toBe("day");
    expect(lightsOf(night)).toBe("night");
    expect(lightsOf({ ...day, phase: "work", activity: [] })).toBe("day");
  });

  it("maps phase to the panel of your side", () => {
    expect(sideFor("gather")).toBe("gather");
    expect(sideFor("brief")).toBe("brief");
    expect(sideFor("work")).toBe("work");
    expect(sideFor("decide")).toBe("decide");
    expect(sideFor("commit")).toBe("commit");
    expect(sideFor("make")).toBe("live");
    expect(sideFor("live")).toBe("live");
    expect(sideFor("ended")).toBe("ended");
  });

  it("places the room on the rail from its phase, and shows Change only when one is real", () => {
    expect(momentIndex({ phase: "gather", change: null })).toBe(0);
    expect(momentIndex({ phase: "work", change: null })).toBe(2);
    expect(momentIndex({ phase: "make", change: null })).toBe(4);
    const change = { text: "", from: null, moved: [], asked: [], untouched: 0 };
    expect(momentIndex({ phase: "live", change })).toBe(5);
    expect(momentIndex({ phase: "ended", change })).toBe(6);
  });

  it("has one class for the phone layout", () => {
    expect(layoutClass(true)).toBe("tb--phone");
    expect(layoutClass(false)).toBe("tb--wide");
  });
});

describe("start my part", () => {
  const req = (kind: string, id: string) => ({
    id: `${kind}:${id}:1:u`,
    kind,
    subjectId: id,
    revision: 1,
    message: "",
  });
  it("covers commitments then tasks and nothing else", () => {
    const list = [req("task", "t"), req("plan", "p"), req("commitment", "c"), req("charter", "x")];
    expect(partRequests(list).map((r) => r.kind)).toEqual(["commitment", "task"]);
  });
  it("answers each through `answer`, in order", async () => {
    const sent: unknown[] = [];
    const ack = await answerAll([req("commitment", "c"), req("task", "t")], async (a) => {
      sent.push(a);
      return { seq: sent.length, signature: "sig" };
    });
    expect(sent).toEqual([
      { interrupt_id: "commitment:c:1:u", consent: true },
      { interrupt_id: "task:t:1:u", consent: true },
    ]);
    expect(ack.seq).toBe(2);
  });
  it("stops at the first refusal and says how far it got", async () => {
    let n = 0;
    await expect(
      answerAll([req("commitment", "c"), req("task", "t")], async () =>
        n++ === 0 ? { seq: 1, signature: "s" } : undefined,
      ),
    ).rejects.toThrow(/1 of 2 answered/);
    expect(n).toBe(2);
  });
});

describe("exports", () => {
  const all = SCENES[8]?.room.results ?? [];
  const of = (kind: string) => {
    const r = all.find((x) => x.kind === kind);
    if (!r) throw new Error(kind);
    return r;
  };
  const draft = { ...of("place"), kind: "draft", data: { subject: "Hello", body: "Come along." } };
  it("offers one export per kind: csv for budget and list, ics for schedule, none for place and draft", () => {
    expect(exportsFor(of("budget")).map((e) => e.label)).toEqual(["Export .csv"]);
    expect(exportsFor(of("schedule")).map((e) => e.label)).toEqual(["Export .ics"]);
    expect(exportsFor(of("place"))).toEqual([]);
    expect(exportsFor(draft)).toEqual([]);
    expect(exportsFor({ ...of("budget"), data: { rows: [] } })).toEqual([]);
  });
  it("makes the budget csv with unwrapped amounts and the total", () => {
    expect(budgetCsv(of("budget"))).toBe(
      "label,amount,currency,provenance\r\nMaterials,120,EUR,vault\r\nSnacks,60,EUR,estimate\r\nTotal,180,EUR,\r\n",
    );
  });
  it("makes a list csv and quotes what needs it", () => {
    const r = {
      ...of("place"),
      kind: "list",
      data: { items: [{ label: "a,b", who: "p1", provenance: "vault" }] },
    };
    expect(listCsv(r)).toBe('label,who,provenance\r\n"a,b",p1,vault\r\n');
  });
  it("makes the schedule ics from items with a start", () => {
    const ics = toIcs(of("schedule")) ?? "";
    expect(ics).toContain("DTSTART:20261107T090000Z");
    expect(ics).toContain("LOCATION:Venue 1");
    expect(toIcs({ ...of("schedule"), data: { items: [{ title: "x" }] } })).toBeNull();
  });
  it("copies text by kind", () => {
    expect(toText(draft)).toBe("Hello\n\nCome along.");
    expect(toText(of("place"))).toContain("Venue 1 (chosen): Free on all three days");
  });
});
