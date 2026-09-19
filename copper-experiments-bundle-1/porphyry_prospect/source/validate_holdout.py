"""Hold-one-out validation: for each positive reference site, retrain the
scorer on the other positives and check whether the held-out site's own
neighborhood is still ranked highly, without that site in training.

This is the plan's central validation requirement: "hold out one known
deposit at a time to confirm the model can correctly identify it without
having trained on it."

For each held-out site we run search_by_chips with that site's chip
removed from positive_chip_ids, restricted to a small bounding box
(+/- ~0.125 deg, ~14 km) around the held-out site's own coordinates, and
record where -- if at all -- a hit close to the true location shows up in
the top-K for that local box. A tight-radius top hit is a clear pass; a
same-district-but-offset top hit (a few km away, inside a known sprawling
district like Yerington or Mineral Park) is a partial pass; no nearby hit
at all is a fail.

Usage:
    python source/validate_holdout.py --tenant-id ten_xxx --collection-id col_xxx
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from lgnd_client import LGNDClient
from score_prospects import haversine_km, load_labels

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "outputs"

BOX_HALF_WIDTH_DEG = 0.125
TOP_K = 15
TIGHT_PASS_KM = 3.0
PARTIAL_PASS_KM = 15.0


def bbox_geometry(lat: float, lon: float, half_width: float = BOX_HALF_WIDTH_DEG) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - half_width, lat - half_width],
            [lon + half_width, lat - half_width],
            [lon + half_width, lat + half_width],
            [lon - half_width, lat + half_width],
            [lon - half_width, lat - half_width],
        ]],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--labels", default=str(DATA_DIR / "labels_resolved.csv"))
    parser.add_argument("--out", default=str(OUTPUTS_DIR / "holdout_validation.csv"))
    args = parser.parse_args()

    labels = load_labels(args.labels)
    positives = [r for r in labels if r["label"] == "positive" and r["chip_id"]]
    negative_ids = [r["chip_id"] for r in labels if r["label"] == "negative" and r["chip_id"]]

    client = LGNDClient.from_env()

    OUTPUTS_DIR.mkdir(exist_ok=True)
    fieldnames = ["held_out_site_id", "true_lat", "true_lon", "best_hit_chip_id",
                  "best_hit_lat", "best_hit_lon", "best_hit_rank", "best_hit_score",
                  "km_from_true_location", "verdict"]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for held_out in positives:
            other_positive_ids = [r["chip_id"] for r in positives if r["site_id"] != held_out["site_id"]]
            true_lat, true_lon = float(held_out["chip_centroid_lat"]), float(held_out["chip_centroid_lon"])

            hits = client.search_by_chips(
                tenant_id=args.tenant_id,
                collection_id=args.collection_id,
                positive_chip_ids=other_positive_ids,
                negative_chip_ids=negative_ids,
                ranking_model="centroid_difference",
                geometry=bbox_geometry(true_lat, true_lon),
                top_k=TOP_K,
            )

            best = None
            best_km = math.inf
            for rank, hit in enumerate(hits, start=1):
                lon, lat = hit["centroid"]["coordinates"]
                km = haversine_km(true_lat, true_lon, lat, lon)
                if km < best_km:
                    best, best_km, best_rank = hit, km, rank

            if best is None:
                verdict = "fail_no_hits_in_box"
                row = {
                    "held_out_site_id": held_out["site_id"], "true_lat": true_lat,
                    "true_lon": true_lon, "best_hit_chip_id": "", "best_hit_lat": "",
                    "best_hit_lon": "", "best_hit_rank": "", "best_hit_score": "",
                    "km_from_true_location": "", "verdict": verdict,
                }
            else:
                if best_km <= TIGHT_PASS_KM:
                    verdict = "pass_tight"
                elif best_km <= PARTIAL_PASS_KM:
                    verdict = "pass_same_district"
                else:
                    verdict = "fail_no_nearby_hit"
                lon, lat = best["centroid"]["coordinates"]
                row = {
                    "held_out_site_id": held_out["site_id"], "true_lat": true_lat,
                    "true_lon": true_lon, "best_hit_chip_id": best["chip_id"],
                    "best_hit_lat": round(lat, 5), "best_hit_lon": round(lon, 5),
                    "best_hit_rank": best_rank, "best_hit_score": round(best["score"], 4),
                    "km_from_true_location": round(best_km, 2), "verdict": verdict,
                }
            writer.writerow(row)
            print(f"{held_out['site_id']}: {row['verdict']} ({row.get('km_from_true_location', 'n/a')} km)")

    print(f"\nWrote hold-one-out results to {args.out}")


if __name__ == "__main__":
    main()
