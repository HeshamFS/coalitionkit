// SPDX-License-Identifier: Apache-2.0
// Smoke test against a mocked host: real SSE over HTTP, reached through the dev server same-origin
// proxy (see CK_PROXY_TARGET in playwright.config.ts), so no host address ever leaves the page.
import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { expect, test } from "@playwright/test";

const PORT = 4599;
const TOKEN = "tok-1";
let server: Server;
const answers: unknown[] = [];
const auths: (string | undefined)[] = [];

const send = (res: ServerResponse, event: object) =>
  res.write(`data: ${JSON.stringify(event)}\n\n`);

const snapshot = {
  coalition_id: "c1",
  events: {
    e1: { type: "coalition.charter", seq: 1, payload: { goal: "Goal 1" } },
    e2: { type: "coalition.join", seq: 2, payload: {} },
    e3: { type: "coalition.join", seq: 3, payload: {} },
  },
};

const surface = [
  { version: "v0.9", createSurface: { surfaceId: "s1", catalogId: "coalitionkit/v0_9" } },
  {
    version: "v0.9",
    updateComponents: {
      surfaceId: "s1",
      components: [
        { id: "root", component: "Column", children: ["h", "task"] },
        { id: "h", component: "Heading", text: { path: "/title" }, variant: "h2" },
        {
          id: "task",
          component: "TaskCard",
          task_id: "t1",
          title: "Task 1",
          status: "proposed",
          assignee: { seat: "1", label: "Member 1" },
        },
      ],
    },
  },
  {
    version: "v0.9",
    updateDataModel: { surfaceId: "s1", path: "/", value: { title: "Surface 1" } },
  },
];

function feed(req: IncomingMessage, res: ServerResponse) {
  res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" });
  send(res, { type: "RUN_STARTED", threadId: "th", runId: "r1" });
  send(res, { type: "STATE_SNAPSHOT", snapshot });
  send(res, {
    type: "ACTIVITY_SNAPSHOT",
    messageId: "a2ui:s1",
    activityType: "a2ui-surface",
    content: { messages: surface },
    replace: true,
  });
  setTimeout(() => {
    send(res, {
      type: "STATE_DELTA",
      delta: [
        { op: "add", path: "/events/e4", value: { type: "coalition.need", seq: 4, payload: {} } },
      ],
    });
  }, 600);
  req.on("close", () => res.end());
}

function agent(req: IncomingMessage, res: ServerResponse) {
  res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" });
  send(res, { type: "RUN_STARTED", threadId: "th-a", runId: "ra1" });
  send(res, {
    type: "RUN_FINISHED",
    threadId: "th-a",
    runId: "ra1",
    outcome: {
      type: "interrupt",
      interrupts: [
        {
          id: "plan:p1:2:u1",
          reason: "consent_required",
          message: "Your decision is needed on a plan",
          metadata: { subject: { kind: "plan", id: "p1", revision: 2 } },
        },
      ],
    },
  });
  req.on("close", () => res.end());
}

test.beforeAll(async () => {
  server = createServer((req, res) => {
    auths.push(req.headers.authorization);
    if (req.headers.authorization !== `Bearer ${TOKEN}`) {
      res.writeHead(401).end();
      return;
    }
    if (req.url === "/v1/feed") return feed(req, res);
    if (req.url === "/v1/agent") return agent(req, res);
    if (req.url === "/v1/agent/answers" && req.method === "POST") {
      let body = "";
      req.on("data", (c) => {
        body += c;
      });
      req.on("end", () => {
        answers.push(JSON.parse(body));
        res
          .writeHead(200, { "Content-Type": "application/json" })
          .end(JSON.stringify({ status: "accepted", seq: 9 }));
      });
      return;
    }
    res.writeHead(404).end();
  });
  await new Promise<void>((ok) => server.listen(PORT, "127.0.0.1", ok));
});

test.afterAll(async () => {
  server.closeAllConnections();
  await new Promise((ok) => server.close(ok));
});

test("sign in, draw the room from the feed, apply a delta and answer a consent request", async ({
  page,
}) => {
  await page.goto("/?token=must-not-be-read");
  await expect(page).not.toHaveURL(/token=/);
  await page.getByLabel("Viewer token").fill(TOKEN);
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByRole("banner").getByText("Goal 1")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Surface 1" })).toBeVisible();
  await expect(page.getByRole("article", { name: "Task Task 1, proposed" })).toBeVisible();

  const needs = page.getByRole("button", { name: /^Needs/ });
  await expect(needs).toContainText("1");

  await expect(page.getByText("1 decision waits for you")).toBeVisible();
  await page.getByRole("button", { name: "Decide" }).click();
  await page.getByRole("button", { name: "Accept" }).click();
  await expect.poll(() => answers.length).toBe(1);
  expect(answers[0]).toEqual({ interrupt_id: "plan:p1:2:u1", consent: true });

  expect(auths.every((a) => a === `Bearer ${TOKEN}`)).toBe(true);
  expect(await page.evaluate(() => location.href)).not.toContain(TOKEN);
});
