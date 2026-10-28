# Live results (measured)

Written by the `live` tests when run with `COALITIONKIT_LIVE=1`. Cost is from the
price table 2026-10-28 applied to the usage the API reported.

| test | model | latency s | prompt tok | completion tok | reasoning tok | cost micro-USD | note |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| chat hosted_agent (minimal) | muse-spark-1.3 | 2.14 | 15 | 19 | 9 | 100 | one word |
| chat composer (low) | muse-spark-1.3 | 2.34 | 15 | 110 | 100 | 487 | one word |
| chat contributor tier | muse-spark-1.3-contributor | 1.76 | 15 | 94 | 84 | 21 | synthetic prompt |
| chat gardener = Muse Wonder | muse-wonder-1.0 | 3.89 | 15 | 46 | 36 | 980 | chat completions |
| steward on Meta route | muse-spark-1.3 | 1.30 | 15 | 45 | 35 | 210 | legacy opts as sent |
| tool call | muse-spark-1.3 | 0.54 | 554 | 85 | 19 | 1054 | args={'key': 'alpha'} |
| strict json_schema | muse-spark-1.3 | 1.45 | 17 | 84 | 62 | 379 | {"name": "triangle", "sides": 3} |
| vision input | muse-spark-1.3 | 0.59 | 36 | 74 | 64 | 360 | 96x96 red PNG |
| image generation | muse-image-1.0 | 9.98 | 0 | 0 | 0 | 10000 | 62612 B b'RIFFWEBP' |
| SAM segment | sam-3.1 | 1.41 | 0 | 0 | 0 | 2500 | 5 circles ['lossless'] |
| transcription PUSH_TO_TALK | muse-voice-transcribe-1.0 | 2.19 | 0 | 0 | 0 | 236 | 4645 ms audio, 0 turn(s) |
| transcription ENDPOINTING | muse-voice-transcribe-1.0 | 1.89 | 0 | 0 | 0 | 236 | 4645 ms audio, 1 turn(s) |
| transcription DIARIZATION | muse-voice-transcribe-1.0 | 2.23 | 0 | 0 | 0 | 236 | 4645 ms audio, 1 turn(s) |

Total live cost: 16799 micro-USD ($0.016799)
