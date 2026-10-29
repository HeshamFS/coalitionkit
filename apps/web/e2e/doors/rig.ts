// SPDX-License-Identifier: Apache-2.0
// Starts the real coalitionkit-server through packages/server/tests/doors_rig.py and talks to it
// over stdin and stdout: one JSON line per command, one per answer.
import { type ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { createInterface } from "node:readline";

export type Ready = {
  ready: true;
  base: string;
  coalition: string;
  tokens: Record<string, string>;
};
export type Audience = "coalition" | string[];

export class Rig {
  private waiting: ((line: Record<string, unknown>) => void)[] = [];
  private constructor(
    private readonly child: ChildProcessWithoutNullStreams,
    readonly info: Ready,
  ) {}

  static async start(root: string, port: number): Promise<Rig> {
    const uv = process.env.UV_BIN ?? "uv";
    const child = spawn(
      uv,
      ["--directory", root, "run", "python", "packages/server/tests/doors_rig.py"],
      { env: { ...process.env, DOORS_RIG_PORT: String(port) }, stdio: ["pipe", "pipe", "pipe"] },
    );
    child.stderr.on("data", () => {});
    const lines = createInterface({ input: child.stdout });
    const first = new Promise<Ready>((resolve, reject) => {
      child.once("exit", (code) => reject(new Error(`rig exited early (${code})`)));
      lines.on("line", (line) => {
        if (!line.startsWith("{")) return;
        const parsed = JSON.parse(line) as Record<string, unknown>;
        if (parsed.ready) resolve(parsed as unknown as Ready);
      });
    });
    const info = await first;
    const rig = new Rig(child, info);
    lines.on("line", (line) => {
      if (!line.startsWith("{")) return;
      const parsed = JSON.parse(line) as Record<string, unknown>;
      if (parsed.ready) return;
      rig.waiting.shift()?.(parsed);
    });
    return rig;
  }

  /** Submit one signed observation and return the wall-clock time the host accepted it. */
  emit(as: string, content: string, audience: Audience): Promise<number> {
    return new Promise((resolve) => {
      this.waiting.push((line) => resolve(Number(line.accepted_ms)));
      this.child.stdin.write(`${JSON.stringify({ op: "emit", as, content, audience })}\n`);
    });
  }

  async stop(): Promise<void> {
    this.child.stdin.write(`${JSON.stringify({ op: "quit" })}\n`);
    await new Promise<void>((resolve) => {
      const timer = setTimeout(() => {
        this.child.kill();
        resolve();
      }, 15_000);
      this.child.once("exit", () => {
        clearTimeout(timer);
        resolve();
      });
    });
  }
}
