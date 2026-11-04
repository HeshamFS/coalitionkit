# WhatsApp channel

A member can take part from a WhatsApp thread. The door sends what the member needs to see as messages, and short replies answer it.

## Set it up

Install `coalitionkit[whatsapp]` and set all four of these. The channel mounts only when all four are present.

| Variable | From |
|---|---|
| `COALITIONKIT_WHATSAPP_TOKEN` | Your WhatsApp Business app |
| `COALITIONKIT_WHATSAPP_PHONE_NUMBER_ID` | The sending number |
| `COALITIONKIT_WHATSAPP_APP_SECRET` | Used to verify that webhooks came from Meta |
| `COALITIONKIT_WHATSAPP_VERIFY_TOKEN` | A value you choose, for webhook setup |

The host needs a public HTTPS address for the webhook. Point your Meta app at the channel's webhook route on that address.

## Invite a member

`POST /admin/whatsapp/invitations` with the admin token, the `coalition` and the `participant` returns a code. The member sends that code to your number to bind the thread to their seat.

## Consent

A message cannot carry a press and hold. When a decision needs a signature, the member gets a link to a confirm page on the host: `COALITIONKIT_CONFIRM_LINK_BASE`, or `/confirm` on the public address.

## Limits

Only the signed-in member's thread gets their private view. Test against your own number: messages cost money on real accounts, and delivery depends on Meta's rules for the template and the recipient.
