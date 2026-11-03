// SPDX-License-Identifier: Apache-2.0
// Local stand-ins for the host's routes, for the gallery and the tests only. They answer at once
// and remember what they were asked, so a test can read it back.
import type { RoomIo } from "./api";

export type Call = { name: string; args: unknown[] };

export function mockIo(calls: Call[] = []): RoomIo {
  const log = (name: string, ...args: unknown[]) => calls.push({ name, args });
  return {
    begin: async (helpers) => {
      log("begin", helpers);
      return { ok: true, data: { phase: "brief" } };
    },
    brief: async (id, answer) => {
      log("brief", id, answer);
      return { ok: true, data: { status: "ok" } };
    },
    say: async (text) => {
      log("say", text);
      if (/phone|password/i.test(text)) {
        return {
          ok: true,
          data: {
            route: "room",
            reply: "That would share private contact details.",
            stopped: true,
          },
        };
      }
      if (/can.?t|cannot|won.?t/i.test(text)) {
        return { ok: true, data: { route: "change", reply: "I asked the people it touches." } };
      }
      return {
        ok: true,
        data: { route: "private", reply: "Noted. I will use this and not share it." },
      };
    },
    done: async (id) => {
      log("done", id);
      return { ok: true, data: { seq: 50 } };
    },
    viewAs: async (who) => {
      log("viewAs", who);
      return {
        ok: true,
        data: {
          messages: [
            {
              version: "v0.9",
              createSurface: { surfaceId: "view-as", catalogId: "coalitionkit/v0_9" },
            },
            {
              version: "v0.9",
              updateComponents: {
                surfaceId: "view-as",
                components: [
                  {
                    id: "root",
                    component: "Text",
                    text: `You and ${who} both see the seats and the needs.`,
                  },
                ],
              },
            },
          ],
        },
      };
    },
  };
}
