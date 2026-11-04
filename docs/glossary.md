# Glossary

| Word | Meaning |
|---|---|
| **A2A** | The Agent2Agent protocol. The Coalition Protocol is an extension of A2A 1.0 |
| **A2UI** | A declarative format for agent-written screens. CoalitionKit uses a closed catalog of it |
| **AG-UI** | A protocol for streaming agent state to a screen. The room feed uses it |
| **Agent key** | The key on a member's card. It signs the member's messages, and can never sign consent |
| **Brief** | The few questions your agent asks you before making offers. Your answers stay in your vault |
| **Canary** | A marked private value that a test watches for, to catch a leak |
| **Card** | A signed description of an agent, as in A2A |
| **Catalog** | The closed list of 201 components a model may use on a screen |
| **Charter** | The signed statement of a room's goal, seats, deadline and rules |
| **Coalition** | A group of people and agents working toward one goal. A **room** is one seen on a screen |
| **Commitment** | A member's promise to do a task. It needs its owner's signed yes |
| **Connector** | A program a pack brings that joins a room from outside, as a business agent |
| **Consent** | A person's signed answer, given by press and hold |
| **Decider** | A member whose yes a plan needs |
| **Discipline Pack** | A folder of data that teaches the room a field of work |
| **Dissolve** | Ending a room, which erases its private data |
| **Door** | A short code that lets people take a seat in a room |
| **Edge** | An adapter that turns outside input into observations with sources |
| **Gardener** | The host's planner. It drafts needs and builds plans by fixed rules |
| **Genesis** | Starting a room from a sentence |
| **Helper** | An agent that fills an empty seat. It is labelled as an agent, and never decides |
| **Host** | The server running a coalition. It orders the log and enforces the rules |
| **Hosted seat** | A seat whose keys and vault the host holds |
| **Lesson** | A short skill written from the log when a room ends |
| **Log** | The signed, hash-linked, append-only record of a room |
| **MCP** | The Model Context Protocol. One way for an agent to join a room |
| **Member** | A participant's agent in a room |
| **Mint** | The part of the kit that makes small agents from fixed templates, with tests |
| **Need** | Something the group has to get done |
| **Offer** | A member's statement that it could take on a need, and at what cost |
| **Owner key** | The key a person holds. It signs consent, and only they can use it |
| **Plan** | A proposed assignment of tasks to members |
| **Projection** | A message delivered with a field hidden or tailored to its viewer, signed by the host |
| **PSI** | Private set intersection. Two vaults learn what they share and nothing else |
| **Receipt** | The host's signed statement that the log reached a given length and head hash |
| **Result** | The thing a task produced, such as a list, a schedule or a draft |
| **Ripple** | A change that reopens only the tasks it touches |
| **Scope** | Who may see an event. The host enforces it |
| **Seat** | A place in a room for a person or an agent |
| **Skill** | A `SKILL.md` that tells an agent how to act |
| **Steward** | The independent checker. Fixed policies run first, then a model audit |
| **Surface** | A screen a viewer sees. Also a tree of catalog components |
| **The Table** | The one living screen that shows a room |
| **Tension** | A vote the room raises when plans pull in different directions |
| **Vault** | The private store behind a member |
| **Viewer token** | The credential a person or agent uses to act as one seat |
