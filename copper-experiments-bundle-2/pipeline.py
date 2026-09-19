#!/usr/bin/env python3
"""Global copper porphyry halo prospector — training + global search + GeoJSON export.

    python pipeline.py --collection-id col_XXXX --top-k 500 --out webapp/data

Requires LGND_API_KEY / LGND_TENANT_ID. The collection must be one that indexes source.coop
imagery beyond CONUS — a CONUS-clipped collection will simply return no candidates outside
the US.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from deposits import KNOWN_HOLDOUT, TRAIN_NEGATIVE, Site, training_set

BASE_URL = "https://embeddings.api.lgnd.ai/v1"
SELF_MATCH_RADIUS_KM = 5.0  # a result within this of a TRAINING site is a self-match, not a find
REIDENTIFY_RADIUS_KM = 15.0  # a result within this of a HELD-OUT known deposit counts as re-identified


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class LgndClient:
    def __init__(self, api_key: str, tenant_id: str, collection_id: str):
        self.tenant_id = tenant_id
        self.collection_id = collection_id
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def _url(self, path: str) -> str:
        return f"{BASE_URL}/tenants/{self.tenant_id}/collections/{self.collection_id}/{path}"

    def nearest_chip_id(self, lat: float, lon: float) -> str | None:
        resp = requests.post(
            self._url("search-by-location"),
            headers=self.headers,
            json={"latitude": lat, "longitude": lon, "top_k": 1},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return data[0]["chip_id"] if data else None

    def search_by_chips(self, positive_chip_ids, negative_chip_ids, top_k: int) -> list[dict]:
        resp = requests.post(
            self._url("search-by-chips"),
            headers=self.headers,
            json={
                "positive_chip_ids": positive_chip_ids,
                "negative_chip_ids": negative_chip_ids,
                "ranking_model": "centroid_difference",
                "top_k": top_k,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


def resolve_chip_ids(client: LgndClient, sites: list[Site]) -> dict[str, str]:
    """site.name -> chip_id, skipping sites the collection has no coverage for."""
    resolved = {}
    for s in sites:
        chip_id = client.nearest_chip_id(s.lat, s.lon)
        if chip_id is None:
            print(f"  [skip] no chip near {s.name} ({s.lat}, {s.lon}) in this collection", file=sys.stderr)
            continue
        resolved[s.name] = chip_id
    return resolved


def sites_to_geojson(sites: list[Site], role: str) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s.lon, s.lat]},
                "properties": {"name": s.name, "country": s.country, "note": s.note, "role": role},
            }
            for s in sites
        ],
    }


def classify_result(centroid_lat, centroid_lon, train_sites, holdout_sites) -> tuple[str, str | None]:
    for s in train_sites:
        if haversine_km(centroid_lat, centroid_lon, s.lat, s.lon) <= SELF_MATCH_RADIUS_KM:
            return "self_match", s.name
    for s in holdout_sites:
        if haversine_km(centroid_lat, centroid_lon, s.lat, s.lon) <= REIDENTIFY_RADIUS_KM:
            return "reidentified_known", s.name
    return "candidate", None


def results_to_geojson(results, train_sites, holdout_sites) -> dict:
    features = []
    for r in results:
        centroid = r.get("centroid", {}).get("coordinates")
        if not centroid:
            continue
        lon, lat = centroid
        bucket, matched_name = classify_result(lat, lon, train_sites, holdout_sites)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "chip_id": r["chip_id"],
                    "score": r["score"],
                    "datetime": r.get("datetime"),
                    "collection": r.get("collection"),
                    "bucket": bucket,
                    "matched_known_site": matched_name,
                    "thumbnail_url": f"{BASE_URL}/chips/{r['chip_id']}/thumbnail",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--collection-id", default=os.environ.get("LGND_COLLECTION_ID"))
    ap.add_argument("--train-set", default="us5", choices=["us5", "global12"])
    ap.add_argument("--top-k", type=int, default=500)
    ap.add_argument("--out", default="webapp/data")
    args = ap.parse_args()

    load_dotenv()
    api_key = os.environ.get("LGND_API_KEY")
    tenant_id = os.environ.get("LGND_TENANT_ID")
    if not api_key or not tenant_id or not args.collection_id:
        sys.exit(
            "Missing credentials: set LGND_API_KEY and LGND_TENANT_ID (.env or env vars) "
            "and pass --collection-id (or set LGND_COLLECTION_ID)."
        )

    client = LgndClient(api_key, tenant_id, args.collection_id)
    train_positive = training_set(args.train_set)

    print(f"Resolving {len(train_positive)} positive + {len(TRAIN_NEGATIVE)} negative training sites...")
    pos_chip_ids = resolve_chip_ids(client, train_positive)
    neg_chip_ids = resolve_chip_ids(client, TRAIN_NEGATIVE)
    if len(pos_chip_ids) < 2 or len(neg_chip_ids) < 2:
        sys.exit("Collection has too little coverage of the training sites to search — pick a global collection.")

    print(f"Searching globally (top_k={args.top_k}, ranking_model=centroid_difference)...")
    results = client.search_by_chips(list(pos_chip_ids.values()), list(neg_chip_ids.values()), args.top_k)
    print(f"  {len(results)} results")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    known_fc = {
        "type": "FeatureCollection",
        "features": (
            sites_to_geojson(train_positive, "train_positive")["features"]
            + sites_to_geojson(TRAIN_NEGATIVE, "train_negative")["features"]
            + sites_to_geojson(KNOWN_HOLDOUT, "holdout")["features"]
        ),
    }
    (out_dir / "known_deposits.geojson").write_text(json.dumps(known_fc, indent=2))

    candidates_fc = results_to_geojson(results, train_positive, KNOWN_HOLDOUT)
    (out_dir / "candidates.geojson").write_text(json.dumps(candidates_fc, indent=2))

    buckets = {}
    for f in candidates_fc["features"]:
        b = f["properties"]["bucket"]
        buckets[b] = buckets.get(b, 0) + 1
    print(f"Wrote {out_dir}/known_deposits.geojson and {out_dir}/candidates.geojson")
    print(f"  buckets: {buckets}")


if __name__ == "__main__":
    main()
