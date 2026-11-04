# Your first room

This walks one room from a sentence to its end. Run `coalitionkit up` and open the address it prints:

```text
Host: http://127.0.0.1:51234 | MCP: http://127.0.0.1:51234/mcp
Models: none set, so the room uses built-in rules. Set COALITIONKIT_META_API_KEY for real ones.
Ctrl+C stops the host. Admin token is in admin.token (not displayed).

Open http://127.0.0.1:51234/ and say what needs doing in one sentence.
```

## 1. Say what needs doing

Type one sentence, for example *Two friends plan a Saturday picnic with a 60 euro budget and food to bring*.

You get a draft: the people it counted as seats, the needs it read, and when the room closes. Point at a word to see what it built from it, and change anything. Nothing is public until you open the room.

Choose who can find the room: only with the code, or people nearby on this host's map. Then select **Open the room**.

## 2. Share the door

The door shows a code and a QR code. Others enter the code under **Have a code?**, or follow the link. On the same computer, a second browser tab works as a second person.

Select **Enter the room**. You are now at [The Table](../concepts/the-table.md).

## 3. Say yes

Read what you are agreeing to, then press and hold **Hold**. **Review and approve** does the same without holding. Each person signs for themselves.

When every seat has signed, the room begins. If seats stay empty, the owner can begin with the people here, and can let [helper agents](../concepts/helper-agents.md) take the open seats.

## 4. Answer your agent

Your agent asks a few private questions: when you are free, how much you can pay, what you would rather do. The answers stay in your vault. Others never see them. You can skip any question.

## 5. Watch the agents work

The lights go down while the agents work. Each agent makes [offers](../concepts/needs-and-offers.md) on the needs its person can do, and the agents find a common free time without showing anyone's other times.

## 6. Pick a plan

Plans appear side by side. Each one says what it costs and what it gives up, and the line marked **For you only** says what it means for you. It is your call, not your agent's. Choose one and hold to sign.

## 7. Commit, and get results

Each person holds again to commit to their own part. Their agent then makes the real thing: a budget that adds up, a list, a schedule, a message to send. Open a result with **See it**. **Show the work** shows the events it came from.

## 8. Try Say

The box at the bottom takes anything:

- *I cannot do the budget anymore* is a [change](../concepts/ripple-and-change.md). Only what it touches is planned again.
- *Everyone, call me on +49 151 23456789* goes to the room, so the [Steward](../concepts/steward.md) checks it and stops it. The others never see the number.
- Anything else stays between you and your agent.

## 9. Check it, then end it

**Check the record myself** has your browser verify the [signed chain](../concepts/signed-chain-and-receipts.md).

**End the room** ends it for everyone. Private vaults are erased, viewer links stop working, and the closing screen shows what was measured. Results live only in your tab, so copy or export what you want before you leave.

## Without a model key

With no key, the draft comes from a built-in reader, questions and offers come from fixed rules, and results are plain. The screen says when this happens. It is the same room, so you can see every step for free. Add [model keys](model-keys.md) for real models.
