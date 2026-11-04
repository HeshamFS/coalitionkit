# Lessons as skills

When a room ends, the host writes a short **lesson** from the log, so the next room can learn from it. It is what remains of a room's experience once its private data is gone.

A [Discipline Pack](../guides/packs/skills-and-lessons.md) brings its own lesson templates. Without one, a generic lesson records the goal, the members, the tasks, the allocation, the decisions, the changes, the policy outcomes and the duration.

## What it holds

A lesson is filled from selected fields of the log and from the record of which pack policies fired, including on messages that were refused, using a fixed set of placeholders. It takes a policy's id and action from that record, not the message. Vault contents never enter a lesson.

Like anything the host derives, a lesson takes the narrowest scope of what it came from. It is shown only to members who could see every source. It can still name the goal and the people in the room, so treat lessons as you treat the log.

## Where it goes

The host stores the lesson as a skill, and the room's last event records its id. The owner's closing screen names it.

In a later room with the same pack and version, a member whose key is in the lesson's audience is offered it along with the pack's skills. Rooms without a pack share lessons the same way. Nobody else is offered it.
