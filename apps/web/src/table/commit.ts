// SPDX-License-Identifier: Apache-2.0
// "Start my part": one gesture, and each of the viewer's open commitment and task requests is
// answered through the trusted `answer`, one after the other. Nothing is answered that the host
// did not list for this viewer, and a refusal stops the run so the rest still wait.
import type { ConsentAcknowledgement } from "../components/f08/ConsentSeal";
import { type Answer, answerFor } from "../feed/actions";
import type { OpenRequest } from "../feed/agent";
import type { AnswerOutcome } from "../feed/useFeed";

/** The requests "Start my part" covers: commitments first, then their tasks. */
export function partRequests(requests: OpenRequest[]): OpenRequest[] {
  const mine = requests.filter((r) => r.kind === "commitment" || r.kind === "task");
  return [...mine.filter((r) => r.kind === "commitment"), ...mine.filter((r) => r.kind === "task")];
}

/**
 * Answers each request in turn. A request the host says is no longer open was already closed by an
 * earlier yes in the same run (a commitment's yes closes the task under it), so it counts as
 * handled, not as a failure. Anything else stops the run and says how far it got.
 */
export async function answerAll(
  requests: OpenRequest[],
  outcome: (a: Answer, quiet?: boolean) => Promise<AnswerOutcome>,
): Promise<{ answered: number; handled: number; last: ConsentAcknowledgement | undefined }> {
  let last: ConsentAcknowledgement | undefined;
  let answered = 0;
  let handled = 0;
  for (const request of requests) {
    const done = await outcome(answerFor(request, true), true);
    if (done.ok) {
      answered += 1;
      last = done.ack;
    } else if (done.error === "not_open") {
      handled += 1;
    } else {
      const why = done.detail ? `${done.error}: ${done.detail}` : done.error;
      throw new Error(
        `${answered} of ${requests.length} answered. The host stopped at the next one (${why}), so the rest still wait for you.`,
      );
    }
  }
  return { answered, handled, last };
}
