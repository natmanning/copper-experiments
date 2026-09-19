# Copper Porphyry Halo Prospect Screening — MVP Project Plan

## 1. Goal

Build an MVP workflow that ingests open and LGND earth observation imagery, learns the
spectral, structural, and textural signature of known porphyry Cu-Mo(-Au) systems with
documented peripheral Pb-Zn-Ag halos, and generates a ranked shortlist of prospects
globally where a similar halo signature appears but no known deposit has been reported.

The v1 output is a ranked shortlist plus a simple map of prospect coordinates with
confidence scores and the evidence behind each score — a first-pass geological
reconnaissance aid, not a drill-ready result.

## 2. Core hypothesis

Porphyry Cu systems have a learnable multi-sensor fingerprint: SWIR/hyperspectral
alteration zoning (argillic to phyllic to propylitic), a thermal-infrared silica
signature in upper lithocap zones, and a radial/concentric structural pattern visible in
synthetic-aperture radar and elevation data. If we encode this fingerprint from known
deposits and compare it against imagery at scale using LGND's earth observation search
and similarity capabilities, we should correctly identify known deposits as a sanity
check and surface a few genuinely novel prospects.

## 3. Known reference sites (training and validation set)

Start with well-documented, spatially compact examples — avoid large sprawling
districts in the reference set since labeling gets noisy at that scale.

- Bingham Canyon, Utah, USA — the reference zoning model; has some pit disturbance, so
  the pit center should be excluded from training imagery
- Mineral Park, Arizona, USA — clean concentric Cu to Pb-Zn to Au-Ag zoning
- Bisbee, Arizona, USA — polymetallic replacement radiating from the stock
- Santa Rita / Chino, New Mexico, USA — Pb-Zn-Ag production tied to a porphyry stock
- Yerington, Nevada, USA — a tilted, exhumed system, useful for studying different
  erosion levels
- Sierrita / Twin Buttes / Pima district, Arizona, USA — same belt, adds sample
  diversity without a new geologic setting
- Sepon, Laos — a contrast case with no Pb-Zn-Ag zone, useful for reducing false
  positives
- Wafi-Golpu, Papua New Guinea — different belt and climate, useful for testing
  generalization

Before training, pull precise deposit outlines and coordinates from a proper source
(USGS MRDS, the USGS Porphyry Copper Deposits of the World compilation, or public
NI 43-101 technical reports) rather than relying on approximate locations. Add four to
six more sites from Andean and Southwest Pacific belts once the workflow runs end to
end, for geographic and climatic diversity.

## 4. Data sources

Open data to use first: Sentinel-2 for SWIR-based alteration mapping, Sentinel-1 radar
for structural and lineament mapping, ASTER for its still-usable visible/near-infrared
and thermal bands plus historical SWIR archive, Copernicus elevation data for
topographic derivatives, EMIT for opportunistic free hyperspectral coverage, and USGS
MRDS or the Porphyry Copper Deposits of the World database as the reference-label
source. National geological surveys sometimes publish open magnetics or radiometric
surveys worth checking per region.

LGND stack: pull imagery and embeddings around each reference site as positive
training examples using LGND's location- and similarity-based search capabilities. Use
LGND's natural-language search as an early qualitative check on what the embedding
space already associates with these locations. Train a lightweight scoring model
directly on the embeddings from labeled positive and negative sites — this is likely
the fastest path to a working v1. Use LGND's geometric filtering to limit the search
area to known porphyry belts (the Andean belt, Southwest Pacific, Basin and Range,
etc.) rather than covering the whole globe in v1. Comparing image pairs over time can
wait for v2, if it becomes useful as a validation signal for known development.

Tasked or registration-gated hyperspectral sources like PRISMA and EnMAP are v2 —
worth registering for early given lead times, but not needed for the MVP.

## 5. MVP approach

Start by assembling reference labels: known deposit coordinates and rough footprint
shapes from the list above, plus contrast examples — random background sites and,
where identifiable, sites that look geologically similar but have no known deposit.

For feature building, pull LGND embeddings for the reference and contrast sites, and
optionally supplement with hand-computed ASTER band ratios as an interpretable
secondary feature set rather than a replacement for the embeddings.

Limit the search area to known metallogenic belts using geometric filtering rather than
covering the globe — this substantially reduces false positives for a first pass.

For scoring, train a lightweight model on the reference and contrast embeddings, score
imagery within the limited belts, rank by confidence, and group nearby high-scoring
results to avoid redundant prospects.

Produce a ranked prospect list (coordinates, score, nearest known deposit for
reference), a simple map visualization — a static plotted map is fine for MVP — and a
short evidence summary per top prospect.

Validation matters more than anything else here: hold out one known deposit at a time
to confirm the model can correctly identify it without having trained on it, and
manually check top prospects against public mining claims or geological survey records
to filter out trivial false positives like active pits or urban areas.

## 6. Explicitly out of scope for MVP

No custom hyperspectral pixel-unmixing or mineral-chemistry work, no
magnetics/gravity/radiometric fusion, no drill-target-grade confidence claims, no
unbounded global search, and no airborne or registration-gated hyperspectral in v1.
All of that is v2+.

## 7. Suggested repo layout (described, not as commands)

A data folder holding the reference site list, contrast site list, and belt boundary
shapes for scoping. A source folder holding scripts for label assembly, feature
building from LGND, scoring-model training, belt-wide evaluation, and validation. An
outputs folder for the ranked prospect list and map. A notebooks folder for exploratory
work. This plan file at the repo root for reference.

## 8. Success criteria for the MVP demo

The workflow runs end to end on at least two belts. Hold-one-out validation correctly
identifies held-out known deposits above a random baseline. The output includes a
ranked prospect list with at least a few geologically plausible, previously unflagged
anomalies worth a geologist's second look. Runtime and cost stay low enough to re-run
belt by belt as labels and features improve.

## 9. Immediate next steps

Pull precise reference coordinates from USGS MRDS or the Porphyry Copper Deposits of
the World database to replace the placeholder locations above. Build out the reference
and contrast site lists as structured data. Confirm LGND has usable imagery coverage at
each reference site before building anything further. Get the lightweight scoring
model working on the small labeled set before scaling to a full belt evaluation.

---

See `README.md` in this directory for the current implementation status, what has
actually been run against live LGND data, and what remains before this plan's success
criteria are fully met.
