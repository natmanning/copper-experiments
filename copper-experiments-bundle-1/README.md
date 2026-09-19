# Copper porphyry halo prospect screening — bundle for copper-experiments

Two pieces, both already built and tested against live LGND data:

- `porphyry_prospect/` — the underlying data + reproducible pipeline: reference/contrast
  site catalogs, resolved LGND chip IDs, scoring + hold-one-out validation scripts,
  and the CSV/PNG results from a live run against the Basin & Range belt.
  See `porphyry_prospect/README.md` for the full writeup of what was run and found.

- `webapp/` — the interactive map front-end. Open `webapp/index.html` in a browser
  (or serve the folder with e.g. `python3 -m http.server` from inside `webapp/`) to
  browse the CONUS-wide prospect results: 5 trained reference deposits, 9 known
  porphyry districts the model re-discovered without training on them (Morenci,
  Miami-Inspiration-Globe, Tyrone, Ray Mine, Robinson/Ely), and ~21 unlabeled
  candidate clusters flagged for manual review, each with score, coordinates, and a
  plain-language region note. Leaflet is vendored locally under `webapp/vendor/` so
  it has no build step and no CDN dependency.

## To add this to natmanning/copper-experiments

```bash
git clone https://github.com/natmanning/copper-experiments.git
cp -r porphyry_prospect webapp copper-experiments/
cd copper-experiments
git add porphyry_prospect webapp
git commit -m "Add porphyry Cu halo prospect screening MVP + interactive map"
git push origin main
```

## Honest caveats (see porphyry_prospect/README.md for the full list)

- This LGND account currently only has embedding collections for the continental US,
  California (NAIP), and France (Sentinel-2) — no true global coverage yet. The map's
  "CONUS-wide" results are the widest search actually runnable right now.
- A public global Sentinel-2 embedding archive exists at
  `https://source.coop/clay/lgnd-embeddings` for genuinely worldwide search, but it
  was unreachable from the sandboxed environment this was built in (network egress
  policy blocks that domain there) — from your own machine/environment it may well
  be reachable, and is the natural next step to actually go global.
- None of the flagged candidates have been checked against USGS MRDS or active mining
  claims yet — do that before treating any of them as a real lead.
- `search_by_chips` with `linear_svm`/`logistic_regression` ranking 500'd at this
  label count (5 positive / 5 negative); `centroid_difference` is what actually
  worked and is what both the pipeline and the map's results use.
