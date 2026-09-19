# Global Copper Porphyry Halo Prospector

Recreates this repo's [Copper Halo prospect mapper](https://natmanning.github.io/copper-experiments/copper-experiments-bundle-1/webapp/)
on the full LGND embedding archive instead of a CONUS-only extract, so it can rank candidate
sites anywhere source.coop imagery (Sentinel-2, NAIP, and whatever else a collection indexes)
has been embedded with Clay.

## Method

Porphyry Cu-Mo(-Au) systems weather into a visually distinctive halo — Pb-Zn-Ag-bearing
alteration rings around the ore body — that shows up in a Clay embedding's texture/color
signature even without a spectral mineral index. The pipeline:

1. **Resolve** each reference deposit's lat/lon to its nearest indexed chip
   (`search-by-location`).
2. **Learn** the halo signature from those chips via `search-by-chips` with
   `ranking_model: "centroid_difference"` — the same method, and the same non-default ranking
   override, the original bundle used (`positive_chip_ids` = known deposits,
   `negative_chip_ids` = non-mineralized control sites).
3. **Search globally** — no `geometry` filter, so every chip in the collection is ranked,
   not just one country.
4. **Split the output** into three buckets: self-matches near the training sites, held-out
   known deposits the model re-identifies without having trained on them (a sanity check on
   the halo signature), and unvetted candidate prospects.

Results are reconnaissance guidance, not drill targets — same caveat as the original.

## Setup

```bash
pip install -r requirements.txt
export LGND_API_KEY=sk_...
export LGND_TENANT_ID=ten_...
```

`pipeline.py` does not default the collection — list your tenant's collections and pick (or
create) one with global coverage:

```bash
curl -s https://embeddings.api.lgnd.ai/v1/tenants/$LGND_TENANT_ID/collections \
  -H "Authorization: Bearer $LGND_API_KEY" | jq '.data[] | {id, name, model}'
```

## Run

```bash
python pipeline.py --collection-id col_XXXX --top-k 500 --out webapp/data
```

Writes `webapp/data/known_deposits.geojson` (training + held-out reference sites) and
`webapp/data/candidates.geojson` (ranked global results, tagged `self_match` /
`reidentified_known` / `candidate`). Add `--train-set global12` to train on a
continent-spanning positive set instead of the original 5 US deposits, if you want the halo
signature itself to be less US/Sentinel-biased.

## View

`webapp/index.html` is a static Leaflet page — no build step, no API key for the basemap
(Esri World Imagery + OpenStreetMap, both key-free XYZ endpoints). Open it directly or serve
it:

```bash
python -m http.server 8080 --directory webapp
```

It ships with `webapp/data/known_deposits.geojson` pre-populated (real, cited deposit
locations) so the reference layer renders immediately. `candidates.geojson` ships as an empty
`FeatureCollection` — the app shows a banner until you run `pipeline.py` with real API
credentials; nothing on the candidates layer is fabricated.

## Current limitations

- Needs an LGND API key with access to a **global** (not CONUS-clipped) Clay collection.
- `centroid_difference` on 5v5 examples is the same coarse method the original bundle used;
  `linear_svm` (the new default `ranking_model`) trains an ephemeral probe per query and may
  separate the halo signature from background better at global scale — worth an A/B once you
  have real results back.
- Chip size/tiling and revisit cadence vary by collection, so `centroid` distance thresholds
  used to bucket "self-match vs re-identified vs candidate" (`SELF_MATCH_RADIUS_KM` in
  `pipeline.py`) may need tuning per collection.
