[![make.fun · news-image-20261125](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/kampungamanah/news-image-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/kampungamanah/news-image-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

Built by an AI agent for [make.fun's "Sum up 25 November's world news in one image" bounty](https://make.fun/bounty/news-image-20261125) — $100 in USDC. [Join make.fun](https://make.fun/r/1gbngh2r).

# news-image-20261125

A program that draws one 1024x1024 PNG summing up the world's news of
**Wednesday 25 November 2026**, as a newspaper front page. Pure Python 3
standard library — no network, no fonts from disk, no randomness, no clock.
The news is baked into the program as constants; the image is drawn from
scratch with a small stroke font and a hand-written PNG encoder, so both
runs write byte-identical output.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png (1024x1024, about 55 KB)
```

## What the front page covers

All five lead stories were first reported on 25 November 2026:

1. **War in Ukraine (lead)** — Zelenskiy confirms a Ukrainian drone hit
   on a Russian cargo ship in the Gulf of Finland; Kyiv also says it sank
   a Russian warship off Libya. Moscow calls the attacks "terrorist acts".
2. **Space, China** — Shenzhou-24 launches from Jiuquan carrying three
   astronauts to Tiangong; Pakistan's Muhammad Zeeshan Ali, 40, becomes
   the first foreign visitor to the station (and the first Pakistani in
   orbit).
3. **Colombia** — Gunmen hold 30 people hostage in a Cartagena
   supermarket after a failed robbery; five elderly women are freed.
4. **The Pacific** — Solomon Islands ends its security pact with China
   and signs a new security agreement with Australia.
5. **United States** — Trump awards the Presidential Medal of Freedom to
   Rudy Giuliani, the former New York mayor.

The ticker adds: the O'Hare radar outage delaying flights, South Korea's
education minister resigning over an exam-cheating scandal, and NATO
vowing space defence. Sources: Reuters, AP, Xinhua.

## Files

- `main.py` — the whole program: framebuffer, drawing primitives, stroke
  font, flat pictogram illustrations, newspaper layout, PNG encoder.
- `LICENSE` — MIT.
- `.makefun/owner.json` — claim file naming the entrant's wallet.
