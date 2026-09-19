"""Score a belt for porphyry-halo similarity and write a ranked, deduped prospect list.

Reads data/labels_resolved.csv for positive/negative chip IDs, runs
search_by_chips against a belt geometry from data/belts.geojson, clusters
nearby hits (the plan's "group nearby high-scoring results to avoid
redundant prospects" step) with a simple grid dedupe, tags each cluster
against a small catalog of known porphyry Cu districts so a human reviewer
can immediately see "already-known deposit" vs "candidate worth a second
look", and writes outputs/ranked_prospects.csv.

Usage:
    python source/score_prospects.py --tenant-id ten_xxx --collection-id col_xxx \
        --belt-id basin_and_range_sw_us --ranking-model centroid_difference

Note on ranking_model: linear_svm and logistic_regression train an
ephemeral linear probe server-side and are the more principled choice once
label counts grow, but at the label counts used for this MVP (5 positive /
5 negative) both returned HTTP 500 from the live API during development.
centroid_difference worked reliably and is the default here; retry the
probe methods once you have >= ~10 examples per class.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from lgnd_client import LGNDClient

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "outputs"

# Well-known porphyry Cu districts near the Basin & Range MVP belt, used only
# to label a ranked hit as "known deposit rediscovered" vs "candidate" for a
# human reviewer -- NOT used anywhere in the scoring/training itself.
KNOWN_DISTRICTS = [
    ("Morenci", 33.0500, -109.3000),
    ("Miami-Inspiration-Globe", 33.3990, -110.8700),
    ("Tyrone", 32.6700, -108.3700),
    ("Robinson (Ely)", 39.2500, -114.8700),
    ("Safford-Lone Star", 32.8500, -109.7500),
    ("Ray Mine", 33.1700, -110.9800),
]

CLUSTER_GRID_DEG = 0.05  # ~5 km grid cell used to dedupe nearby hits
KNOWN_DISTRICT_RADIUS_KM = 15


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_labels(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def load_belt_geometry(belt_id: str) -> dict:
    belts = json.loads((DATA_DIR / "belts.geojson").read_text())
    for feature in belts["features"]:
        if feature["properties"]["belt_id"] == belt_id:
            return feature["geometry"]
    raise KeyError(f"No belt with id {belt_id!r} in belts.geojson")


def cluster_hits(hits: list[dict]) -> list[dict]:
    """Grid-snap nearby hits into one row each, keeping the best score per cell."""
    best_by_cell: dict[tuple[int, int], dict] = {}
    for hit in hits:
        lon, lat = hit["centroid"]["coordinates"]
        cell = (round(lat / CLUSTER_GRID_DEG), round(lon / CLUSTER_GRID_DEG))
        if cell not in best_by_cell or hit["score"] > best_by_cell[cell]["score"]:
            best_by_cell[cell] = hit
    return sorted(best_by_cell.values(), key=lambda h: -h["score"])


def nearest_known_district(lat: float, lon: float) -> tuple[str, float]:
    best_name, best_km = "none", math.inf
    for name, dlat, dlon in KNOWN_DISTRICTS:
        km = haversine_km(lat, lon, dlat, dlon)
        if km < best_km:
            best_name, best_km = name, km
    return best_name, best_km


def nearest_training_site(lat: float, lon: float, labels: list[dict]) -> tuple[str, float]:
    best_id, best_km = "none", math.inf
    for row in labels:
        if row["label"] != "positive" or not row["chip_centroid_lat"]:
            continue
        km = haversine_km(lat, lon, float(row["chip_centroid_lat"]), float(row["chip_centroid_lon"]))
        if km < best_km:
            best_id, best_km = row["site_id"], km
    return best_id, best_km


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--belt-id", default="basin_and_range_sw_us")
    parser.add_argument("--ranking-model", default="centroid_difference",
                         choices=["centroid_difference", "linear_svm", "logistic_regression"])
    parser.add_argument("--top-k", type=int, default=80)
    parser.add_argument("--labels", default=str(DATA_DIR / "labels_resolved.csv"))
    parser.add_argument("--out", default=str(OUTPUTS_DIR / "ranked_prospects.csv"))
    args = parser.parse_args()

    labels = load_labels(args.labels)
    positive_ids = [r["chip_id"] for r in labels if r["label"] == "positive" and r["chip_id"]]
    negative_ids = [r["chip_id"] for r in labels if r["label"] == "negative" and r["chip_id"]]
    if not positive_ids:
        raise SystemExit("No positive chip IDs found -- run label_assembly.py first.")

    client = LGNDClient.from_env()
    geometry = load_belt_geometry(args.belt_id)

    hits = client.search_by_chips(
        tenant_id=args.tenant_id,
        collection_id=args.collection_id,
        positive_chip_ids=positive_ids,
        negative_chip_ids=negative_ids,
        ranking_model=args.ranking_model,
        geometry=geometry,
        top_k=args.top_k,
    )
    clustered = cluster_hits(hits)

    OUTPUTS_DIR.mkdir(exist_ok=True)
    fieldnames = ["rank", "chip_id", "score", "latitude", "longitude",
                  "nearest_training_site_id", "km_to_training_site",
                  "nearest_known_district", "km_to_known_district", "status"]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rank, hit in enumerate(clustered, start=1):
            lon, lat = hit["centroid"]["coordinates"]
            site_id, km_site = nearest_training_site(lat, lon, labels)
            district, km_district = nearest_known_district(lat, lon)
            if km_site <= 5:
                status = "training_site_self_match"
            elif km_district <= KNOWN_DISTRICT_RADIUS_KM:
                status = "known_deposit_rediscovered"
            else:
                status = "candidate_needs_manual_review"
            writer.writerow({
                "rank": rank,
                "chip_id": hit["chip_id"],
                "score": round(hit["score"], 4),
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "nearest_training_site_id": site_id,
                "km_to_training_site": round(km_site, 1),
                "nearest_known_district": district,
                "km_to_known_district": round(km_district, 1),
                "status": status,
            })
    print(f"Wrote {len(clustered)} clustered prospects to {args.out}")


if __name__ == "__main__":
    main()
