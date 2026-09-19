"""Static map of reference deposits, contrast sites, and ranked prospects.

Reads data/reference_sites.csv, data/contrast_sites.csv, and
outputs/ranked_prospects.csv and writes outputs/prospect_map.png.

This intentionally uses a plain matplotlib scatter (no basemap tiles /
cartopy dependency) to keep the MVP dependency-light, per the plan's "a
static plotted map is fine for MVP" guidance.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "outputs"

STATUS_STYLE = {
    "training_site_self_match": dict(marker="^", color="#1b9e77", label="Training site (self-match)"),
    "known_deposit_rediscovered": dict(marker="D", color="#7570b3", label="Known deposit rediscovered (not trained on)"),
    "candidate_needs_manual_review": dict(marker="*", color="#d95f02", label="Candidate — needs manual review"),
}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    reference = [r for r in read_csv(DATA_DIR / "reference_sites.csv")
                 if r["training_role"] == "positive"]
    contrast = read_csv(DATA_DIR / "contrast_sites.csv")
    prospects = read_csv(OUTPUTS_DIR / "ranked_prospects.csv")

    fig, ax = plt.subplots(figsize=(10, 8))

    ax.scatter(
        [float(r["longitude"]) for r in contrast],
        [float(r["latitude"]) for r in contrast],
        marker="x", color="#999999", s=40, label="Contrast / background site", zorder=2,
    )

    seen_labels = set()
    for row in prospects:
        style = STATUS_STYLE[row["status"]]
        label = style["label"] if style["label"] not in seen_labels else None
        seen_labels.add(style["label"])
        size = 90 if row["status"] != "training_site_self_match" else 70
        ax.scatter(float(row["longitude"]), float(row["latitude"]), marker=style["marker"],
                   color=style["color"], s=size, label=label, zorder=3, edgecolor="black", linewidth=0.4)

    ax.scatter(
        [float(r["longitude"]) for r in reference],
        [float(r["latitude"]) for r in reference],
        marker="o", facecolor="none", edgecolor="#e7298a", s=260, linewidth=1.6,
        label="Reference deposit (training positive)", zorder=4,
    )
    for r in reference:
        ax.annotate(r["name"], (float(r["longitude"]), float(r["latitude"])),
                    textcoords="offset points", xytext=(6, 6), fontsize=8, color="#e7298a")

    for row in prospects:
        if row["status"] == "candidate_needs_manual_review":
            ax.annotate(row["nearest_known_district"] if row["km_to_known_district"] and float(row["km_to_known_district"]) < 60 else "?",
                        (float(row["longitude"]), float(row["latitude"])),
                        textcoords="offset points", xytext=(6, -10), fontsize=7, color="#d95f02")

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Porphyry Cu halo prospect screening — Basin & Range MVP run\n"
                  "(CONUS AEF 2022 / LGND embeddings, centroid_difference ranking)")
    ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
    ax.set_aspect("equal")
    fig.tight_layout()

    OUTPUTS_DIR.mkdir(exist_ok=True)
    out_path = OUTPUTS_DIR / "prospect_map.png"
    fig.savefig(out_path, dpi=160)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
