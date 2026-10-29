// SPDX-License-Identifier: Apache-2.0
// Acceptance test 3, the parts the doors lane owns: one state, four roles, and the room, the lens
// and the MCP App view drawing it for each role from a real coalitionkit-server.
//
// Change to paint: the host accepts one observation (the rig answers with the wall-clock time it
// got the acknowledgement); each surface then records, with the same clock, the time its DOM
// shows the change after two animation frames (so the frame carrying it was painted).
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { type Browser, expect as baseExpect, type Frame, type Page, test } from "@playwright/test";
import { RIG_PORT, WEB_PORT } from "../../playwright.doors.config";
import { Rig } from "./rig";

const ROOT = resolve(import.meta.dirname, "../../../..");
const ROLES = ["p1", "p2", "p3", "p4"] as const;
const SURFACES = ["web", "lens", "mcp"] as const;
type Role = (typeof ROLES)[number];
type Surface = (typeof SURFACES)[number];
type Snapshot = { members: number; needs: number; offers: number; plans: number; log: number };

const EXPECTED = JSON.parse(
  readFileSync(resolve(import.meta.dirname, "expected.json"), "utf8"),
) as Record<Role, Snapshot>;
const SAMPLES = 15;
const PASS_P95_MS = 1000;
const MARKER = "private-marker-1";

// A browser keeps at most six connections to one origin, and each open room, lens and MCP host
// holds a live stream or two. Over HTTP/1.1 twelve pages on one origin would starve each other,
// so every role gets its own loopback address (127.0.0.x reaches the same dev server).
const origin = (last: number) => `http://127.0.0.${last}:${WEB_PORT}`;

// The first page load makes the dev server pre-bundle its dependencies; give setup room.
test.use({ actionTimeout: 30_000 });
const expect = baseExpect.configure({ timeout: 30_000 });

type Seat = { page: Page; frame: () => Frame; kind: "kv" | "lens" };

/** Runs in every frame before its scripts: arms a watch for "N log entries" and times the paint. */
function installProbe() {
  const w = window as unknown as {
    __ck: { t: number | null; wire: string; arm: (k: string, n: number) => void };
  };
  // Keep everything this page's browser receives on the feed and agent streams, as text.
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const res = await realFetch(input, init);
    const raw =
      typeof input === "string" ? input : input instanceof Request ? input.url : `${input}`;
    if (!/\/v1\/(feed|agent)$/.test(new URL(raw, location.href).pathname) || !res.body) return res;
    const [mine, theirs] = res.body.tee();
    void (async () => {
      const reader = theirs.getReader();
      const decoder = new TextDecoder();
      for (;;) {
        const chunk = await reader.read().catch(() => ({ done: true, value: undefined }));
        if (chunk.done) return;
        w.__ck.wire += decoder.decode(chunk.value, { stream: true });
      }
    })();
    return new Response(mine, res);
  };
  w.__ck = {
    wire: "",
    t: null,
    arm(kind, n) {
      w.__ck.t = null;
      const ok = () =>
        kind === "lens"
          ? document.querySelector(".lens-title")?.textContent === `${n} log entries`
          : [...document.querySelectorAll("dt")].some(
              (dt) =>
                dt.textContent === "Log entries" &&
                dt.nextElementSibling?.textContent === String(n),
            );
      const mo = new MutationObserver(() => {
        if (w.__ck.t !== null || !ok()) return;
        w.__ck.t = 0;
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            w.__ck.t = Date.now();
            mo.disconnect();
          }),
        );
      });
      mo.observe(document, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true,
      });
    },
  };
}

function readKv(): Record<string, string> {
  return Object.fromEntries(
    [...document.querySelectorAll("dl.kv dt")].map((dt) => [
      dt.textContent ?? "",
      dt.nextElementSibling?.textContent ?? "",
    ]),
  );
}

const num = (v: string | undefined) => Number(v ?? Number.NaN);
const fromKv = (kv: Record<string, string>): Snapshot => ({
  members: num(kv.Members),
  needs: num(kv.Needs),
  offers: num(kv.Offers),
  plans: num(kv.Plans),
  log: num(kv["Log entries"]),
});

async function snapshot(seat: Seat): Promise<Snapshot> {
  if (seat.kind === "kv") return fromKv(await seat.frame().evaluate(readKv));
  // Lens: step 2 holds the counts, step 1 the member count.
  const read = () =>
    seat.page.evaluate(() => ({
      title: document.querySelector(".lens-title")?.textContent ?? "",
      body: document.querySelector(".lens-body")?.textContent ?? "",
    }));
  const counts = await read();
  const m = /^(\d+) log entries$/.exec(counts.title);
  const b = /^(\d+) needs · (\d+) offers · (\d+) plans$/.exec(counts.body);
  await seat.page.getByRole("button", { name: "Swipe back" }).click();
  const first = await read();
  await seat.page.getByRole("button", { name: "Swipe next" }).click();
  const mem = /^(\d+) members?$/.exec(first.body);
  return {
    members: Number(mem?.[1]),
    needs: Number(b?.[1]),
    offers: Number(b?.[2]),
    plans: Number(b?.[3]),
    log: Number(m?.[1]),
  };
}

/** Visit every route once so the dev server finishes pre-bundling before anything is timed. */
async function warm(browser: Browser) {
  const context = await browser.newContext();
  const page = await context.newPage();
  for (const path of ["/", "/lens", "/e2e/host/index.html"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
  }
  await page.waitForTimeout(3000);
  for (const path of ["/", "/lens", "/e2e/host/index.html"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
  }
  await context.close();
}

async function open(
  browser: Browser,
  rig: Rig,
): Promise<{
  seats: Record<Role, Record<Surface, Seat>>;
  mcpRequests: string[];
  close: () => Promise<void>;
}> {
  const context = await browser.newContext({ viewport: { width: 1000, height: 760 } });
  await context.addInitScript(installProbe);
  const mcpRequests: string[] = [];
  const seats = {} as Record<Role, Record<Surface, Seat>>;
  for (const [n, role] of ROLES.entries()) {
    const token = rig.info.tokens[role] as string;
    const sign = (t: string) => sessionStorage.setItem("ck.token", t);

    const web = await context.newPage();
    await web.addInitScript(sign, token);
    await web.goto(`${origin(10 + n)}/`);
    await expect(web.getByText("Log entries")).toBeVisible();

    const lens = await context.newPage();
    await lens.addInitScript(sign, token);
    await lens.goto(`${origin(10 + n)}/lens`);
    await expect(lens.getByRole("heading", { level: 2 })).toBeVisible();
    await lens.getByRole("button", { name: "Swipe next" }).click();
    await expect(lens.locator(".lens-title")).toContainText("log entries");

    const mcp = await context.newPage();
    await mcp.addInitScript(
      (setup) => {
        (window as unknown as { __HOST: unknown }).__HOST = setup;
      },
      { token, coalition: rig.info.coalition },
    );
    mcp.on("request", (r) => {
      if (r.frame() !== mcp.mainFrame()) mcpRequests.push(r.url());
    });
    await mcp.goto(`${origin(20 + n)}/e2e/host/index.html`);
    await mcp.evaluate(() => (window as unknown as { __hostReady: Promise<string> }).__hostReady);
    const find = () => mcp.frames().find((f) => f !== mcp.mainFrame()) as Frame;
    await expect.poll(async () => find()?.locator("[data-testid=mcp-view]").count()).toBe(1);
    await expect(find().getByText("Log entries")).toBeVisible();

    seats[role] = {
      web: { page: web, frame: () => web.mainFrame(), kind: "kv" },
      lens: { page: lens, frame: () => lens.mainFrame(), kind: "lens" },
      mcp: { page: mcp, frame: find, kind: "kv" },
    };
  }
  return { seats, mcpRequests, close: () => context.close() };
}

const carries = (text: string) => text.includes(MARKER);

/** The first complete STATE_SNAPSHOT frame of an SSE response, as its `data: ...` line. */
async function firstSnapshotFrame(res: Response): Promise<string> {
  const reader = (res.body as ReadableStream<Uint8Array>).getReader();
  const decoder = new TextDecoder();
  let text = "";
  for (;;) {
    const chunk = await reader.read();
    if (chunk.done) throw new Error("no snapshot");
    text += decoder.decode(chunk.value, { stream: true });
    const hit = text
      .split("\n\n")
      .find((f) => f.includes('"STATE_SNAPSHOT"') && f.startsWith("data: "));
    if (hit && text.includes(`${hit}\n\n`)) {
      await reader.cancel();
      return hit;
    }
  }
}

/** A room for p2 whose feed carries `snapshot` instead of the real one. */
async function controlPage(browser: Browser, rig: Rig, snapshot: object): Promise<Seat> {
  const context = await browser.newContext({ viewport: { width: 1000, height: 760 } });
  await context.addInitScript(installProbe);
  const page = await context.newPage();
  await page.addInitScript(
    (t) => sessionStorage.setItem("ck.token", t),
    rig.info.tokens.p2 as string,
  );
  await page.route("**/v1/feed", (route) => {
    const frames = [{ type: "RUN_STARTED", threadId: "control", runId: "control-1" }, snapshot];
    return route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: frames.map((f) => `data: ${JSON.stringify(f)}\n\n`).join(""),
    });
  });
  await page.goto(`${origin(40)}/`);
  await expect(page.getByText("Log entries")).toBeVisible();
  return { page, frame: () => page.mainFrame(), kind: "kv" };
}

const percentile = (sorted: number[], p: number) =>
  sorted[Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1)] as number;

test("one state, four roles: the room, the lens and the MCP App view agree and stay in scope", async ({
  browser,
}) => {
  await warm(browser);
  const rig = await Rig.start(ROOT, RIG_PORT);
  const { seats, mcpRequests, close } = await open(browser, rig);
  try {
    // The state: a note for the organizer and observer roles only, then one for everybody.
    await rig.emit("p1", MARKER, ["organizer", "observer"]);
    await rig.emit("p2", "shared-1", "coalition");

    // Each surface of each role shows exactly what that role may see, as recorded.
    for (const role of ROLES) {
      for (const surface of SURFACES) {
        const seat = seats[role][surface];
        await expect
          .poll(() => snapshot(seat), { message: `${role} ${surface}` })
          .toEqual(EXPECTED[role]);
      }
    }
    // Content outside a role's scope reaches no part of what its browser receives: every feed
    // snapshot and delta, every agent-session payload and every MCP tool result, not just the DOM.
    const received = async (seat: Seat) =>
      seat.page.evaluate(() => (window as never as { __ck: { wire: string } }).__ck.wire);
    const mcpData = (role: Role) =>
      seats[role].mcp.page.evaluate(() =>
        JSON.stringify((window as unknown as { __hostLog: unknown }).__hostLog),
      );
    for (const role of ROLES) {
      const sees = role === "p1" || role === "p4";
      for (const surface of ["web", "lens"] as const) {
        const wire = await received(seats[role][surface]);
        // The streams were read at all (guards against an empty capture passing every check).
        expect(wire, `${role} ${surface} wire`).toContain("STATE_SNAPSHOT");
        expect(wire, `${role} ${surface} wire`).toContain("coalition.charter");
        expect(carries(wire), `${role} ${surface} wire`).toBe(sees);
      }
      const log = await mcpData(role);
      expect(log, `${role} mcp data`).toContain("coalition.charter");
      expect(carries(log), `${role} mcp data`).toBe(sees);
      for (const surface of SURFACES) {
        const html = await seats[role][surface].frame().content();
        expect(carries(html), `${role} ${surface} dom`).toBe(false);
      }
    }

    // Negative control: a marker slipped into an existing event of p2's own feed. The counts and
    // the DOM do not change, so the earlier checks would pass; the wire check must catch it.
    const upstream = await fetch(`http://127.0.0.1:${RIG_PORT}/v1/feed`, {
      headers: { Authorization: `Bearer ${rig.info.tokens.p2}` },
    });
    const snapshotFrame = await firstSnapshotFrame(upstream);
    const tampered = JSON.parse(snapshotFrame.slice("data: ".length)) as {
      snapshot: { events: Record<string, { payload: Record<string, unknown> }> };
    };
    const first = Object.values(tampered.snapshot.events)[0];
    if (!first) throw new Error("no event to tamper with");
    first.payload.note = MARKER;
    const control = await controlPage(browser, rig, tampered);
    const tamperedWire = await received(control);
    expect(carries(tamperedWire), "control: marker in p2's stream is caught").toBe(true);
    await expect.poll(() => snapshot(control)).toEqual(EXPECTED.p2); // counts alone would pass
    await control.page.context().close();

    // Pictures of the three surfaces for the owner to compare with the sheets.
    const shots = resolve(import.meta.dirname, "../../test-results/doors");
    mkdirSync(shots, { recursive: true });
    await seats.p1.lens.page.locator(".lens-frame").screenshot({ path: `${shots}/lens-p1.png` });
    await seats.p1.web.page.screenshot({ path: `${shots}/web-p1.png` });
    await seats.p1.mcp.page.screenshot({ path: `${shots}/mcp-p1.png` });

    // Change to paint: the same accepted change, timed on every surface of every role.
    const samples: Record<Surface, number[]> = { web: [], lens: [], mcp: [] };
    const byRole: Record<string, number[]> = {};
    for (let i = 0; i < SAMPLES; i++) {
      for (const role of ROLES) {
        for (const surface of SURFACES) {
          const seat = seats[role][surface];
          const target = EXPECTED[role].log + i + 1;
          await seat
            .frame()
            .evaluate(
              ([k, n]) =>
                (window as never as { __ck: { arm: (k: string, n: number) => void } }).__ck.arm(
                  k as string,
                  n as number,
                ),
              [seat.kind === "lens" ? "lens" : "kv", target],
            );
        }
      }
      const accepted = await rig.emit(ROLES[i % ROLES.length] as string, `tick-${i}`, "coalition");
      for (const role of ROLES) {
        for (const surface of SURFACES) {
          const seat = seats[role][surface];
          await seat.frame().waitForFunction(
            () => {
              const t = (window as never as { __ck: { t: number | null } }).__ck.t;
              return t !== null && t > 0;
            },
            undefined,
            { timeout: 10_000 },
          );
          const t = await seat
            .frame()
            .evaluate(() => (window as never as { __ck: { t: number } }).__ck.t);
          const ms = t - accepted;
          samples[surface].push(ms);
          const key = `${surface}:${role}`;
          byRole[key] = [...(byRole[key] ?? []), ms];
        }
      }
    }

    const report: Record<string, unknown> = {
      measured: new Date().toISOString(),
      definition:
        "ms from the host's acknowledgement of one accepted observation to the second animation frame after the surface's DOM shows it; all four roles and three surfaces watch the same change",
      samplesPerSurface: SAMPLES * ROLES.length,
      passMarkP95Ms: PASS_P95_MS,
    };
    for (const surface of SURFACES) {
      const sorted = [...samples[surface]].sort((a, b) => a - b);
      report[surface] = {
        n: sorted.length,
        p50: percentile(sorted, 50),
        p95: percentile(sorted, 95),
        min: sorted[0],
        max: sorted.at(-1),
      };
    }
    mkdirSync(resolve(import.meta.dirname, "../../test-results"), { recursive: true });
    writeFileSync(
      resolve(import.meta.dirname, "../../test-results/doors-latency.json"),
      `${JSON.stringify(report, null, 2)}\n`,
    );
    console.log(JSON.stringify(report, null, 2));
    for (const surface of SURFACES) {
      const sorted = [...samples[surface]].sort((a, b) => a - b);
      expect(percentile(sorted, 95), `${surface} p95`).toBeLessThan(PASS_P95_MS);
    }

    // The MCP App view asked for nothing outside itself.
    expect(mcpRequests).toEqual([]);
  } finally {
    await close();
    await rig.stop();
  }
});
