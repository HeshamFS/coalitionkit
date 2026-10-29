# Live results (measured)

Written by the `live` tests when run with `COALITIONKIT_LIVE=1`. Cost is from the
price table 2026-10-28 applied to the usage the API reported.

| test | model | latency s | prompt tok | completion tok | reasoning tok | cost micro-USD | note |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| chat hosted_agent (minimal) | muse-spark-1.3 | 1.38 | 15 | 48 | 38 | 223 | one word |
| chat composer (low) | muse-spark-1.3 | 1.08 | 15 | 125 | 115 | 550 | one word |
| chat contributor tier | muse-spark-1.3-contributor | 3.41 | 15 | 174 | 164 | 37 | synthetic prompt |
| chat gardener = Muse Wonder | muse-wonder-1.0 | 2.29 | 15 | 22 | 12 | 500 | chat completions |
| steward on Meta route | muse-spark-1.3 | 1.11 | 15 | 105 | 95 | 465 | legacy opts as sent |
| tool call | muse-spark-1.3 | 1.55 | 554 | 84 | 17 | 1050 | args={'key': 'alpha'} |
| strict json_schema | muse-spark-1.3 | 2.11 | 17 | 114 | 92 | 506 | {"name": "triangle", "sides": 3} |
| vision input | muse-spark-1.3 | 1.21 | 36 | 128 | 118 | 589 | 96x96 red PNG |
| image generation | muse-image-1.0 | 11.42 | 0 | 0 | 0 | 10000 | 53718 B b'RIFFWEBP' |
| SAM segment | sam-3.1 | 1.84 | 0 | 0 | 0 | 2500 | 5 circles ['lossless'] |
| transcription PUSH_TO_TALK | muse-voice-transcribe-1.0 | 2.32 | 0 | 0 | 0 | 236 | 4645 ms audio, 0 turn(s) |
| transcription ENDPOINTING | muse-voice-transcribe-1.0 | 2.28 | 0 | 0 | 0 | 236 | 4645 ms audio, 1 turn(s) |
| transcription DIARIZATION | muse-voice-transcribe-1.0 | 2.48 | 0 | 0 | 0 | 236 | 4645 ms audio, 1 turn(s) |

Total live cost: 17128 micro-USD ($0.017128)
