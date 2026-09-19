"""Thin HTTP client for the LGND geospatial embeddings search API.

This mirrors the tool surface exposed to this project during development
(list_tenants, list_collections, search_by_location, search_by_chips,
get_chip_metadata, get_chip_thumbnail_url) so the rest of the source/
scripts can be re-run outside of an interactive agent session.

Configuration (env vars):
    LGND_API_BASE_URL   Base URL of the LGND search API. No public default is
                         baked in here -- confirm the current value against
                         LGND's API reference before first use.
    LGND_API_KEY         Bearer token / API key for the tenant.

The request paths below follow the same resource shape used during
development (tenant -> collection -> search) but have NOT been verified
against a live deployment from outside an LGND-provided tool. Treat this
module as a starting point: if a call 404s, check the current LGND API
reference and adjust the paths in `_request` accordingly. The method
signatures and return shapes (dicts with a top-level "data" list) are the
part worth keeping stable, since every other script here is written
against them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

DEFAULT_TIMEOUT_S = 60


@dataclass
class LGNDClient:
    base_url: str
    api_key: str
    timeout_s: int = DEFAULT_TIMEOUT_S

    @classmethod
    def from_env(cls) -> "LGNDClient":
        base_url = os.environ.get("LGND_API_BASE_URL")
        api_key = os.environ.get("LGND_API_KEY")
        if not base_url or not api_key:
            raise RuntimeError(
                "Set LGND_API_BASE_URL and LGND_API_KEY before using LGNDClient."
            )
        return cls(base_url=base_url.rstrip("/"), api_key=api_key)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.request(
            method, url, headers=headers, timeout=self.timeout_s, **kwargs
        )
        response.raise_for_status()
        return response.json()

    def list_tenants(self) -> list[dict]:
        return self._request("GET", "/v1/tenants")["data"]

    def list_collections(self, tenant_id: str, bbox: str | None = None) -> list[dict]:
        params = {"tenant_id": tenant_id}
        if bbox:
            params["bbox"] = bbox
        return self._request("GET", "/v1/collections", params=params)["data"]

    def search_by_location(
        self,
        tenant_id: str,
        collection_id: str,
        latitude: float,
        longitude: float,
        top_k: int = 10,
        expand: list[str] | None = None,
    ) -> list[dict]:
        payload = {
            "tenant_id": tenant_id,
            "collection_id": collection_id,
            "latitude": latitude,
            "longitude": longitude,
            "top_k": top_k,
        }
        if expand:
            payload["expand"] = expand
        return self._request("POST", "/v1/search/by-location", json=payload)["data"]

    def search_by_chips(
        self,
        tenant_id: str,
        collection_id: str,
        positive_chip_ids: list[str],
        negative_chip_ids: list[str] | None = None,
        ranking_model: str = "centroid_difference",
        geometry: dict | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        payload: dict[str, Any] = {
            "tenant_id": tenant_id,
            "collection_id": collection_id,
            "positive_chip_ids": positive_chip_ids,
            "ranking_model": ranking_model,
            "top_k": top_k,
        }
        if negative_chip_ids:
            payload["negative_chip_ids"] = negative_chip_ids
        if geometry:
            payload["geometry"] = geometry
        return self._request("POST", "/v1/search/by-chips", json=payload)["data"]

    def get_chip_metadata(self, chip_id: str) -> dict:
        return self._request("GET", f"/v1/chips/{chip_id}")

    def get_chip_thumbnail_url(self, chip_id: str) -> str:
        return self._request("GET", f"/v1/chips/{chip_id}/thumbnail-url")["url"]
