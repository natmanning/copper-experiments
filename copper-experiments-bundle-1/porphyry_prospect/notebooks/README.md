# notebooks/

Exploratory work goes here (e.g. inspecting individual chip thumbnails,
sanity-checking embedding neighborhoods before committing to a scoring
run, trying alternative belt geometries).

No notebook is checked in yet — the MVP run in this repo was driven directly
through `source/*.py` and the LGND search tools rather than a notebook. If
you start one, a natural first cell is loading `outputs/ranked_prospects.csv`
and calling `LGNDClient.get_chip_thumbnail_url(chip_id)` on the
`candidate_needs_manual_review` rows to eyeball them before spending any
geologist time on them.
