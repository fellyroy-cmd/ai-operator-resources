# 09 · Audio

- The reference measures **-14.0 LUFS with a loudness range of only 2 LU**: the voice is very even. So the voice gets
  a high-pass (80 Hz) and gentle compression (-22 dB threshold, 3:1) before the mix, then **two-pass loudnorm to
  -14 LUFS / -1.5 dBTP / LRA 7**.
- Music sits under the voice: volume 0.07 by default, **sidechain-ducked** whenever the creator talks. Above 0.10 it fights the voice.
- SFX are seasoning: whoosh on shot moves and chapter cards, boom on the chapter number, pop per chip/card, click per
  list item or tick, digital/tick on counters and typing. Master level is `SFX_MASTER` in build.py: change it there,
  never per effect.
- No SFX on captions in longform. Music fades in over 1.5s and out over 3s.
