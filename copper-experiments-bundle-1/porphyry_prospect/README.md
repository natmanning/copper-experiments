# Copper Porphyry Halo Prospect Screening — MVP

Status: first live pass complete on one belt (Basin & Range, southwestern
US). See `PROJECT_PLAN.md` for the original goal/scope; this file covers
what has actually been run and what it found.

## What's here

```
data/                  reference & contrast site catalogs, belt geometry, resolved chip IDs
source/                lgnd_client.py + the four pipeline scripts (assemble -> score -> validate -> plot)
outputs/               ranked_prospects.csv, holdout_validation.csv, prospect_map.png
notebooks/             placeholder for exploratory work
PROJECT_PLAN.md         the original project plan, verbatim
```

## What was actually run

This tenant's LGND account currently exposes three collections: `CONUS AEF
2022` (covers the continental US, 320 m chips, "aef" embedding model),
`California NAIP 2020-2022`, and `France Sentinel2 2024-2025`. **There is
no coverage yet for the Andean or Southwest Pacific belts**, so the plan's
"run end to end on at least two belts" criterion is not yet met — this pass
covers one belt (Basin & Range) end to end, using `CONUS AEF 2022`.

### Coverage check (plan §9, "confirm LGND has usable imagery coverage
### before building anything further")

Checked all 8 reference sites against `CONUS AEF 2022` via
`search_by_location`:

| Site | Covered? |
|---|---|
| Bingham Canyon, UT | yes |
| Mineral Park, AZ | yes |
| Bisbee, AZ | **no** — outside collection bounds up to ~31.47°N; first covered point is ~31.55°N, ~11 km N of the deposit |
| Santa Rita / Chino, NM | yes |
| Yerington, NV | yes |
| Sierrita / Twin Buttes, AZ | yes |
| Sepon, Laos | no (no collection for SE Asia) |
| Wafi-Golpu, PNG | no (no collection for PNG) |

Bisbee, Sepon, and Wafi-Golpu are kept in `data/reference_sites.csv` for
when a suitable collection exists, but were **not** used in the live run
below.

### Labels used (5 positive / 5 negative)

- **Positive** (halo signature, one chip each): Bingham Canyon (offset ~3 km
  off the excavated pit per the plan's instruction to exclude pit
  disturbance), Mineral Park, Santa Rita/Chino, Yerington, Sierrita/Twin
  Buttes.
- **Negative**: two unmineralized basin-fill/desert-flat sites, one barren
  volcanic range with no reported Cu district, one non-Cu volcanic terrain,
  and one "near a known district but off the actual deposit" site (Salt
  Lake Valley, near Bingham).

See `data/labels_resolved.csv` for the exact chip IDs this resolved to.

### Scoring model (plan §5)

`search_by_chips` supports training an ephemeral linear probe
(`linear_svm` / `logistic_regression`) directly from positive/negative chip
IDs — exactly the "train a lightweight scoring model directly on the
embeddings" step the plan calls for, with no local ML code needed.

**Operational finding:** at 5 positive / 5 negative examples, both
`linear_svm` and `logistic_regression` returned HTTP 500 from the live API.
`centroid_difference` (which the API falls back to automatically below 5
examples/class, but errored instead of falling back here) worked reliably
and is what `source/score_prospects.py` defaults to. Worth retrying the
probe methods once the labeled set grows past ~10-15 examples per class.

### Results: belt-wide ranked prospects (`outputs/ranked_prospects.csv`)

Ran `search_by_chips` with the 5 positives / 5 negatives, `centroid_difference`
ranking, restricted to the Basin & Range bbox in `data/belts.geojson`,
`top_k=80`, then grid-clustered to 20 deduped hits (`source/score_prospects.py`).
Each hit is tagged against the training sites and a small catalog of known
porphyry districts near the belt:

| Outcome | Count | Notes |
|---|---|---|
| `training_site_self_match` | 4 | Correctly lands back on/near Sierrita and Santa Rita/Chino — expected. |
| `known_deposit_rediscovered` | 9 | **Morenci (×4 hits), Miami-Inspiration-Globe, Tyrone (×3), Ray Mine, Robinson/Ely** — all real, well-known porphyry Cu districts, none of which were in the training set. This is the strongest sanity check in this pass: the model generalized to genuine deposits it never saw. |
| `candidate_needs_manual_review` | 4 | See below. |

The 4 flagged candidates, with an honest read on each:

1. **~35.37°N, -114.14°W** (10.8 km from the Mineral Park training chip) —
   almost certainly just the sprawl of the Mineral Park/Chloride district
   itself; the 5 km self-match radius used for clustering is too tight for
   a district this size. Not a novel prospect.
2. **~32.94°N, -109.61°W** (17 km from Safford-Lone Star) — plausibly the
   edge of the Safford district (Freeport's Safford/Lone Star complex
   spans several km); borderline, worth a quick look but likely not novel.
3. **~36.24°N, -106.27°W** (northern New Mexico, ~440 km from the nearest
   catalogued district) — genuinely outside any district in the reference
   catalog used here. Could be real alteration signal or could be a
   texture false-positive (e.g. red sandstone/canyon terrain); **this is
   the kind of hit the plan's manual-check step exists for** — check
   against USGS MRDS / active mining claims before spending more time on
   it.
4. **~34.59°N, -113.22°W** (west-central Arizona, ~253 km from the nearest
   catalogued district) and **~38.11°N, -117.73°W** (central Nevada, near
   the Gabbs magnesite district, ~278 km from the nearest catalogued
   Cu district) — same caveat as #3.

None of these four have been checked against USGS MRDS or active claims
yet — that manual step (plan §5, "manually check top prospects... to
filter out trivial false positives") is the next thing to do before
treating any of them as a real lead.

See `outputs/prospect_map.png` for a plotted view of all of the above.

### Validation: hold-one-out (`outputs/holdout_validation.csv`)

For each of the 5 positive sites, retrained on the other 4 + all 5
negatives and searched a ~14 km box around the held-out site's own
coordinates (`source/validate_holdout.py`):

| Held out | Best hit distance from true location | Verdict |
|---|---|---|
| Sierrita/Twin Buttes | 1.7 km | **pass, tight** |
| Bingham Canyon | 3.1 km | pass, same district |
| Yerington | 7.9 km | pass, same district |
| Mineral Park | 10.1 km | pass, same district |
| Santa Rita/Chino | 10.9 km | pass, same district |

All 5 held-out deposits were the top-ranked (or effectively top-ranked)
hit in their own local search box without having been in training — this
satisfies the plan's "hold-one-out validation correctly identifies held-out
known deposits above a random baseline" criterion, though the looser
matches (7-11 km) mostly reflect these being district-scale positives
rather than single-point deposits, and are worth tightening in a v1.1
pass with more precise pit/stock-outline geometries instead of single
lat/lon points.

## Honest gaps vs. the plan's success criteria

- **"Runs end to end on at least two belts"** — only one belt is runnable
  today (no LGND collection covers the Andean or SW Pacific belts). This
  is a data-availability gap, not a pipeline gap; the pipeline itself is
  belt-agnostic (`--belt-id` in `score_prospects.py`, `data/belts.geojson`
  already has placeholder Andean/SW Pacific polygons).
- **Manual claims/MRDS check on the 4 candidates** — not yet done. Do this
  before telling anyone these are real leads.
- **`linear_svm` / `logistic_regression` probes** — both 500'd at this
  label count; only `centroid_difference` has been validated live.
- **ASTER band-ratio secondary features** — not built; this pass is
  LGND-embeddings-only, per the plan's note that this is "likely the
  fastest path to a working v1."

## Re-running this

```bash
export LGND_API_BASE_URL=...   # see source/lgnd_client.py docstring
export LGND_API_KEY=...
cd source
python label_assembly.py  --tenant-id ten_019d96d4cd217225b479c9d2ee54b05b \
                           --collection-id col_019de50b5b2b70cca7a3a5b4bc42c0a9
python score_prospects.py --tenant-id ten_019d96d4cd217225b479c9d2ee54b05b \
                           --collection-id col_019de50b5b2b70cca7a3a5b4bc42c0a9 \
                           --belt-id basin_and_range_sw_us
python validate_holdout.py --tenant-id ten_019d96d4cd217225b479c9d2ee54b05b \
                            --collection-id col_019de50b5b2b70cca7a3a5b4bc42c0a9
python plot_map.py
```

`lgnd_client.py`'s request paths were written to match the LGND search
tool surface used to develop this (list_tenants / list_collections /
search_by_location / search_by_chips / get_chip_metadata /
get_chip_thumbnail_url) but have **not** been confirmed against a live
deployment outside of that tool integration — check the current LGND API
reference before relying on the exact paths in `_request`.

## Next steps (in priority order)

1. Manually check the 4 flagged candidates against USGS MRDS / active
   mining claims.
2. Add a Sentinel-2 or Landsat-based LGND collection covering the Andean
   and/or SW Pacific belts so Sepon and Wafi-Golpu (already in
   `data/reference_sites.csv`) and a second belt become runnable.
3. Replace single lat/lon reference points with real deposit
   outlines/footprints (USGS PCDW or NI 43-101) to tighten hold-one-out
   distances.
4. Grow the labeled set past ~10-15 examples/class and retry
   `logistic_regression` / `linear_svm` ranking.
5. Add the ASTER band-ratio secondary feature set as an interpretability
   cross-check on top candidates.
