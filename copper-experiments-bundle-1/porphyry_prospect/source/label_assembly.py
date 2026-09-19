"""Resolve reference/contrast site coordinates to LGND chip IDs.

Reads data/reference_sites.csv and data/contrast_sites.csv, looks each
site up against a collection via search_by_location, and writes
data/labels_resolved.csv -- the table that score_prospects.py and
validate_holdout.py consume.

Usage:
    python source/label_assembly.py --collection-id col_xxx --tenant-id ten_xxx

The current data/labels_resolved.csv in this repo was produced by running
this same lookup interactively against the CONUS AEF 2022 collection; this
script lets you regenerate it (or extend it to a new collection/belt).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from lgnd_client import LGNDClient

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_sites(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def resolve_site(client: LGNDClient, tenant_id: str, collection_id: str, site: dict):
    lat, lon = float(site["latitude"]), float(site["longitude"])
    try:
        results = client.search_by_location(
            tenant_id=tenant_id,
            collection_id=collection_id,
            latitude=lat,
            longitude=lon,
            top_k=1,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced in the output row
        return {"chip_id": "", "chip_centroid_lon": "", "chip_centroid_lat": "",
                "resolved_via": f"search_by_location -> ERROR: {exc}"}
    if not results:
        return {"chip_id": "", "chip_centroid_lon": "", "chip_centroid_lat": "",
                "resolved_via": "search_by_location -> no results"}
    top = results[0]
    centroid = top["centroid"]["coordinates"]
    return {
        "chip_id": top["chip_id"],
        "chip_centroid_lon": centroid[0],
        "chip_centroid_lat": centroid[1],
        "resolved_via": "search_by_location(top_k=1)",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--out", default=str(DATA_DIR / "labels_resolved.csv"))
    args = parser.parse_args()

    client = LGNDClient.from_env()

    reference = load_sites(DATA_DIR / "reference_sites.csv")
    contrast = load_sites(DATA_DIR / "contrast_sites.csv")

    rows: list[dict] = []
    for site in reference:
        if site["training_role"] not in ("positive", "excluded", "excluded_no_coverage"):
            continue
        label = {
            "positive": "positive",
            "excluded": "excluded",
            "excluded_no_coverage": "excluded_no_coverage",
        }[site["training_role"]]
        resolved = resolve_site(client, args.tenant_id, args.collection_id, site)
        rows.append({
            "site_id": site["site_id"],
            "label": label,
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "collection_id": args.collection_id,
            **resolved,
        })

    for site in contrast:
        resolved = resolve_site(client, args.tenant_id, args.collection_id, site)
        rows.append({
            "site_id": site["site_id"],
            "label": "negative",
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "collection_id": args.collection_id,
            **resolved,
        })

    fieldnames = ["site_id", "label", "latitude", "longitude", "collection_id",
                  "chip_id", "chip_centroid_lon", "chip_centroid_lat", "resolved_via"]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} resolved labels to {args.out}")


if __name__ == "__main__":
    main()
