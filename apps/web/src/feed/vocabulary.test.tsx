// SPDX-License-Identifier: Apache-2.0
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { orderPanels } from "./views";
import { makeWord, packWords, useVocabulary, VocabularyProvider, wordsOf } from "./vocabulary";

const withPack = (pack: unknown) => ({ pack });

describe("word()", () => {
  it("falls back to the core word without a pack", () => {
    const word = wordsOf(null);
    expect(word("task")).toBe("task");
    expect(word("task", 3)).toBe("tasks");
    expect(word("need", 1)).toBe("need");
    expect(word("offer", 0)).toBe("offers");
  });

  it("uses a pack plural by count and a bare string for every count", () => {
    const word = makeWord({ task: { one: "job", other: "jobs" }, need: "ask" });
    expect(word("task")).toBe("job");
    expect(word("task", 1)).toBe("job");
    expect(word("task", 2)).toBe("jobs");
    expect(word("need", 5)).toBe("ask");
  });

  it("keeps the core word for a key the pack does not rename, and an unknown key as given", () => {
    const word = makeWord({ task: "job" });
    expect(word("offer", 2)).toBe("offers");
    expect(word("steward")).toBe("steward");
  });

  it("ignores malformed vocabulary in the state", () => {
    const state = withPack({ vocabulary: { task: 7, need: { one: "a" }, offer: "", plan: "map" } });
    expect(packWords(state)).toEqual({ plan: "map" });
  });
});

function Probe() {
  const { word } = useVocabulary();
  return <p>{`${word("task")}|${word("task", 2)}`}</p>;
}

describe("useVocabulary", () => {
  it("reads core words outside a provider", () => {
    render(<Probe />);
    expect(screen.getByText("task|tasks")).toBeTruthy();
  });
  it("reads the pack words inside one", () => {
    const state = withPack({ vocabulary: { task: { one: "job", other: "jobs" } } });
    render(
      <VocabularyProvider state={state}>
        <Probe />
      </VocabularyProvider>,
    );
    expect(screen.getByText("job|jobs")).toBeTruthy();
  });
});

const join = (roles: string[]) => ({
  e1: { seq: 1, type: "coalition.join", on_behalf_of: "p1", payload: { roles_requested: roles } },
});

describe("orderPanels", () => {
  const defaults = ["ParticipantCard", "PlanCompare"];
  const state = (roles = ["lead"]) => ({
    viewer: "p1",
    events: join(roles),
    pack: {
      views: {
        order: {
          lead: { wide: ["PlanCompare", "PackOnly", "Mystery"], compact: ["ParticipantCard"] },
        },
        components: { PackOnly: { props: [], required: [], doors: [] } },
      },
    },
  });

  it("is unchanged without a pack", () => {
    expect(orderPanels(null, "wide", defaults)).toEqual(defaults);
    expect(orderPanels({ viewer: "p1" }, "wide", defaults)).toEqual(defaults);
  });
  it("moves named panels first for the role and device, ignoring unknown names", () => {
    expect(orderPanels(state(), "wide", defaults)).toEqual(["PlanCompare", "ParticipantCard"]);
    expect(orderPanels(state(), "compact", defaults)).toEqual(["ParticipantCard", "PlanCompare"]);
  });
  it("does not reorder for a role without an order", () => {
    expect(orderPanels(state(["guest"]), "wide", defaults)).toEqual(defaults);
  });
});
