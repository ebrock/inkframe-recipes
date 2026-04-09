# InkFrame Canonical Recipes

Fujifilm recipe fingerprints curated by [@ebrock](https://github.com/ebrock) for automatic recipe identification in [InkFrame](https://github.com/ebrock/InkFrame).

When you shoot with a known recipe, InkFrame matches your photo's EXIF data against this list and tells you which recipe was used — no manual tagging required.

## How it works

InkFrame computes a deterministic SHA-256 fingerprint from a photo's Fujifilm MakerNote EXIF fields (film simulation, tone curves, white balance, etc.). When a photo's fingerprint matches one in this manifest, the recipe is automatically identified.

The app syncs from `canonical-recipes.json` on launch (once per 24 hours) and merges new recipes into the local library without overwriting any user edits.

## Schema

```json
{
  "version": 1,
  "updatedAt": "2026-04-07T12:00:00Z",
  "recipes": [
    {
      "fingerprint": "a1b2c3d4e5f6g7h8",
      "name": "Kodachrome 64",
      "source": "https://fujixweekly.com/...",
      "sensor": "X-Trans V",
      "recipe": {
        "filmSimulation": "Classic Chrome",
        "highlightTone": "-2",
        "shadowTone": "+1",
        "color": "+3",
        "noiseReduction": "-4",
        "sharpness": "-2",
        "clarity": "-3",
        "grainEffect": "Strong",
        "grainSize": "Large",
        "colorChromeEffect": "Strong",
        "colorChromeFXBlue": "Weak",
        "whiteBalance": "Kelvin",
        "whiteBalanceFineTune": "Red +1, Blue -3",
        "colorTemperature": 5800
      }
    }
  ]
}
```

### Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | `Int` | Schema version (currently `1`) |
| `updatedAt` | `String` | ISO 8601 timestamp of last manifest update |
| `recipes` | `Array` | List of canonical recipe entries |

### Recipe entry fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fingerprint` | `String` | Yes | SHA-256 fingerprint (first 16 hex chars) computed from normalized recipe fields |
| `name` | `String` | Yes | Human-readable recipe name |
| `source` | `String` | No | URL where the recipe was published |
| `sensor` | `String` | No | Target sensor generation (see below) |
| `recipe` | `Object` | Yes | Recipe settings (see below) |

### Sensor values

| Value | Cameras |
|-------|---------|
| `X-Trans II` | X-T1, X-T10, X-E2, X-Pro1, X100T, X100S |
| `X-Trans III` | X-T2, X-T20, X-Pro2, X100F, X-E3, X-H1 |
| `X-Trans IV` | X-T3, X-T4, X-T30, X-Pro3, X-S10, X-E4, X100V |
| `X-Trans V` | X-T5, X-H2, X-H2S, X-S20, X-T50, X100VI, X-M5 |
| `GFX` | GFX series |
| `Bayer` | X-A3, X-A5, X-A7, X-A10, X-A20 |

### Recipe fields

All recipe fields are optional — only include settings that the recipe specifies.

| Field | Type | Values |
|-------|------|--------|
| `filmSimulation` | `String` | `Provia`, `Velvia`, `Astia Soft`, `Classic Chrome`, `Classic Neg`, `Nostalgic Neg`, `Eterna`, `Eterna Bleach Bypass`, `Reala Ace`, `Acros`, `Acros+R`, `Acros+G`, `Acros+Ye`, `Pro Neg Hi`, `Pro Neg Std`, `Sepia` |
| `dynamicRange` | `String` | `Auto`, `DR100`, `DR200`, `DR400` |
| `highlightTone` | `String` | `-2` to `+4` (supports half steps like `-1.5`) |
| `shadowTone` | `String` | `-2` to `+4` (supports half steps like `-1.5`) |
| `color` | `String` | `-4` to `+4` |
| `noiseReduction` | `String` | `-4` to `+4` |
| `sharpness` | `String` | `-4` to `+4` |
| `clarity` | `String` | `-5` to `+5` (X-Trans IV+ only) |
| `grainEffect` | `String` | `Off`, `Weak`, `Strong` |
| `grainSize` | `String` | `Small`, `Large` (X-Trans IV+ only) |
| `colorChromeEffect` | `String` | `Off`, `Weak`, `Strong` |
| `colorChromeFXBlue` | `String` | `Off`, `Weak`, `Strong` |
| `whiteBalance` | `String` | `Auto`, `Daylight`, `Shade`, `Fluorescent`, `Incandescent`, `Underwater`, `Kelvin` |
| `whiteBalanceFineTune` | `String` | e.g. `Red +3, Blue -5` |
| `colorTemperature` | `Int` | Kelvin value (e.g. `5800`) — used when `whiteBalance` is `Kelvin` |

## Fingerprint computation

Fingerprints are computed from normalized recipe values to ensure that equivalent settings always produce the same hash, regardless of how different cameras or tools format the values.

1. **Normalize** each field: strip parenthetical descriptions (e.g. `-2 (soft)` becomes `-2`), snap numeric values to the nearest 0.5, remove sign prefixes on zero values, and treat `Off` / `nil` as empty
2. **Concatenate** all fields in order with `|` as separator: `filmSimulation|dynamicRange|...|colorTemperature`
3. **Hash** with SHA-256 and take the first 8 bytes (16 hex characters)

Fields included in fingerprint (in order): `filmSimulation`, `dynamicRange`, `developmentDynamicRange`, `highlightTone`, `shadowTone`, `color`, `noiseReduction`, `sharpness`, `clarity`, `grainEffect`, `grainSize`, `colorChromeEffect`, `colorChromeFXBlue`, `whiteBalance`, `whiteBalanceFineTune`, `colorTemperature`.

Per-shot fields (`iso`, `exposureCompensation`) are excluded — they vary between shots and would prevent matching photos taken with the same recipe under different conditions.

## Contributing

To suggest a recipe, open an issue using the **Recipe Submission** template. Export the recipe JSON from InkFrame and paste it in. The maintainer will review and apply the `approved` label — a GitHub Action will handle the rest automatically.

The sync service verifies fingerprint integrity on import — entries with mismatched fingerprints are silently skipped.

## Hosting your own canonical repo

This repo follows an open schema. You can fork it (or start fresh) to maintain your own recipe library. InkFrame can be pointed at any URL serving a `canonical-recipes.json` that matches the schema above.

## License

[MIT](LICENSE)
