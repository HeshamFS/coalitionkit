# Live results (measured)

Written by the `live` tests when run with `COALITIONKIT_LIVE=1`. Cost is from the
price table 2026-10-28 applied to the usage the API reported.

| test | model | latency s | prompt tok | completion tok | reasoning tok | cost micro-USD | note |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| chat hosted_agent (minimal) | muse-spark-1.3 | 0.45 | 15 | 25 | 15 | 125 | one word |
| chat composer (low) | muse-spark-1.3 | 0.85 | 15 | 75 | 65 | 338 | one word |
| chat contributor tier | muse-spark-1.3-contributor | 1.10 | 15 | 23 | 13 | 7 | synthetic prompt |
| chat gardener = Muse Wonder | muse-wonder-1.0 | 1.37 | 15 | 39 | 29 | 840 | chat completions |
| steward on Meta route | muse-spark-1.3 | 2.05 | 15 | 142 | 132 | 623 | legacy opts as sent |
| tool call | muse-spark-1.3 | 1.04 | 554 | 82 | 14 | 1041 | args={'key': 'alpha'} |
| strict json_schema | muse-spark-1.3 | 0.83 | 17 | 74 | 52 | 336 | {"name": "triangle", "sides": 3} |
| vision input | muse-spark-1.3 | 1.01 | 36 | 86 | 76 | 411 | 96x96 red PNG |
| image generation | muse-image-1.0 | 9.46 | 0 | 0 | 0 | 10000 | 53842 B b'RIFFWEBP' |
| SAM segment | sam-3.1 | 1.92 | 0 | 0 | 0 | 2500 | 5 circles ['lossless'] |
| transcription PUSH_TO_TALK | muse-voice-transcribe-1.0 | 2.69 | 0 | 0 | 0 | 236 | 4645 ms audio, 0 turn(s) |
| transcription ENDPOINTING | muse-voice-transcribe-1.0 | 2.40 | 0 | 0 | 0 | 236 | 4645 ms audio, 1 turn(s) |
| transcription DIARIZATION | muse-voice-transcribe-1.0 | 1.77 | 0 | 0 | 0 | 236 | 4645 ms audio, 1 turn(s) |

Total live cost: 16929 micro-USD ($0.016929)
