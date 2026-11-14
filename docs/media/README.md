# Spendly app preview

- [Animated phone-frame preview](spendly-preview.gif) — 1080 × 860, five scenes.
- [Static, reduced-motion alternative](spendly-preview.png).
- `screens/`: resized source captures; `sources.json`: original and derivative hashes.

This is a designed **screenshot slideshow**, not a recording of taps or a claim
that every animation occurs in the app. The generic Android-style phone frame,
background and captions are presentation artwork. Screen values are not edited.

The screens are actual native Flutter captures from the authorised Spendly
1.4.1+15 **acceptance build**, using a fictional account and controlled data on
13 November 2026. That build is distinct from the downloadable original release
APK; later source changes are not automatically included in that APK. SMS source
icons come from synthetic fixtures, not access to a personal inbox. Estimates
are not guaranteed outcomes; alerts are review prompts, not fraud findings.

Sequence: transactions → budgets → weekly estimate → alert review → recommendations.
Each screen stays visible for 3.8 seconds, followed by a short crossfade. The
README includes a static-image link and a reduced-motion image source.

Regenerate locally with an existing Pillow installation:

```powershell
python docs/media/build_preview.py
```

The checked-in derivative captures make regeneration independent of a phone,
backend or report archive. When the original local report collection is present,
the builder first checks its manifest hashes and refreshes the derivatives.
It verifies source hashes, GIF frame decoding, dimensions, loop duration and size.
No app build, account access, service launch or dependency installation is needed.
