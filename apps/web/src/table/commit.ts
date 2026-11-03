// SPDX-License-Identifier: Apache-2.0
// "Start my part": one gesture, and each of the viewer's open commitment and task requests is
// answered through the trusted `answer`, one after the other. Nothing is answered that the host
// did not list for this viewer, and a refusal stops the run so the rest still wait.
import type { ConsentAcknowledgement } from "../components/f08/ConsentSeal";
import { type Answer, answerFor } from "../feed/actions";
import type { OpenRequest } from "../feed/agent";

/** The requests "Start my part" covers: commitments first, then their tasks. */
export function partRequests(requests: OpenRequest[]): OpenRequest[] {
  const mine = requests.filter((r) => r.kind === "commitment" || r.kind === "task");
  return [...mine.filter((r) => r.kind === "commitment"), ...mine.filter((r) => r.kind === "task")];
}

export async function answerAll(
  requests: OpenRequest[],
  answer: (a: Answer) => Promise<ConsentAcknowledgement | undefined>,
): Promise<ConsentAcknowledgement> {
  let last: ConsentAcknowledgement | undefined;
  for (const [i, request] of requests.entries()) {
    const ack = await answer(answerFor(request, true));
    if (!ack) {
      throw new Error(
        `${i} of ${requests.length} answered. The host stopped at the next one, so the rest still wait for you.`,
      );
    }
    last = ack;
  }
  if (!last) throw new Error("Nothing is waiting for your yes.");
  return last;
}
