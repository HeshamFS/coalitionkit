# Phone inputs: voice and photo

On a phone, typing is slow. The room takes two other inputs:

- **Voice.** Press the mic button, speak for up to 20 seconds, press it again.
- **Photo.** Press the camera button and take a photo, or pick one.

Both are on the say box at the bottom of the room. Under each brief question there is a second pair.

## What happens to a clip or a photo

1. The phone sends it to the host with your viewer token.
2. The host reads it. A clip goes to the transcriber (`muse-voice-transcribe-1.0`). A photo goes to your own agent's model as an image (`muse-spark-1.3` on the composer route).
3. You see what was read. Nothing is saved or sent yet.
4. You may change the words, then confirm. Only then does the usual route run: `/v1/room/brief` for an answer, `/v1/room/say` for a sentence.

The audio and the image are held in memory for that one call and then dropped. They never enter the log, the store or another person's screen. What was read is kept in your own vault, and your screen lists it as `room.mine.inputs`.

### Answering a question

The host reads the clip or photo into the question's closed kind: one option, some time slots, a number in range or a short text. It uses the same check as a typed answer. When the input does not answer the question, the screen says so and the question stays open. A spoken text answer is the words as heard, and you can change them before you confirm.

### Saying something

A spoken sentence goes the same three ways as a typed one: private, to the room, or a change. Said to the room, it is a `coalition.observe` with `source: "voice"`. A change is a `coalition.ripple` on the needs it touches. The Table shows a mic mark by your seat. For a photo, your agent writes one sentence about it in the first person. If you send it to the room, its source is `camera`.

## The browser side

Browsers record in their own format. Chrome gives WebM with Opus, and iOS Safari gives MP4 with AAC. The page decodes the recording with Web Audio and turns it into 16 kHz mono 16-bit WAV before it leaves the phone, because the transcriber takes WAV only. A photo is scaled down to 1280 pixels on its longest side and sent as JPEG.

You can call the routes yourself:

```bash
curl -X POST "$HOST/v1/room/voice" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: audio/wav" \
  --data-binary @clip.wav

curl -X POST "$HOST/v1/room/photo?question_id=q1" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: image/jpeg" \
  --data-binary @photo.jpg
```

A multipart upload with a part named `audio` or `image` works too. Starlette may write a multipart part over 1 MB to a temporary file until the request ends. The raw body, which the room uses, stays in memory.

The [HTTP routes](../reference/http-routes.md) page lists the answers and refusals.

## HTTPS for the microphone

Browsers allow the microphone only on HTTPS or on `localhost`. A phone on the same Wi-Fi reaches the host over plain HTTP, so the mic button reports that it cannot record. The camera button is a plain file picker, and it works over HTTP too.

For a demo, put the host behind an HTTPS tunnel. Cloudflare's quick tunnel needs no account:

```bash
coalitionkit up --port 8801 --data-dir ./host
cloudflared tunnel --url http://127.0.0.1:8801
```

It prints an address like `https://<name>.trycloudflare.com`. Know these limits before you use it:

- **The room works through it.** The page, the feed, the say box, the brief, voice and photo all use the viewer token, so they work from the tunnel address.
- **Starting and joining do not.** `coalitionkit up` runs with the `local` start setting. Its start and join routes accept only requests whose `Origin` is the host's own `http://127.0.0.1:<port>`. The tunnel address is refused with 403. Invitation links and QR codes also point at `http://127.0.0.1:<port>`, so a phone cannot open them.
- **So seat people on the host machine.** Start the room and accept each invitation at `http://127.0.0.1:<port>`. Then open the tunnel address on the phone, choose **Have a token? Sign in**, and paste that seat's viewer token.
- **The tunnel is public.** Anyone with the address reaches your host. Through the tunnel every request comes from this machine, so a script that sets the host's own `Origin` can still draft and start rooms on your model key. Keep the address private, and stop the tunnel when the demo ends.
