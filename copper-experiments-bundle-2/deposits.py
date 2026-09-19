"""Reference site catalog for the global copper porphyry halo pipeline.

All coordinates are the publicly documented mine/deposit centroid (or, for background sites,
a representative point of the named land cover). Real, citable locations only — nothing here
is a model output.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    name: str
    lat: float
    lon: float
    country: str
    note: str = ""


# The original bundle's 5 training deposits (Basin and Range / Southwest US porphyry belt).
TRAIN_POSITIVE_US5 = [
    Site("Bingham Canyon", 40.5265, -112.1493, "USA", "Utah; largest man-made excavation"),
    Site("Mineral Park", 35.4599, -114.1494, "USA", "Arizona"),
    Site("Santa Rita / Chino", 32.7817, -108.0581, "USA", "New Mexico"),
    Site("Yerington", 38.9911, -119.1633, "USA", "Nevada"),
    Site("Sierrita / Twin Buttes", 31.8386, -111.1653, "USA", "Arizona"),
]

# A continent-spanning alternative training set, for a less US/Sentinel-biased halo signature.
TRAIN_POSITIVE_GLOBAL12 = [
    Site("Bingham Canyon", 40.5265, -112.1493, "USA"),
    Site("Chuquicamata", -22.2967, -68.9036, "Chile"),
    Site("Escondida", -24.2667, -69.0667, "Chile"),
    Site("El Teniente", -34.0850, -70.3500, "Chile"),
    Site("Los Pelambres", -31.7333, -70.4667, "Chile"),
    Site("Cerro Verde", -16.5333, -71.6167, "Peru"),
    Site("Toquepala", -17.2667, -70.6167, "Peru"),
    Site("Cananea", 30.9833, -110.3167, "Mexico"),
    Site("Highland Valley", 50.4833, -121.0000, "Canada"),
    Site("Grasberg", -4.0533, 137.1150, "Indonesia"),
    Site("Oyu Tolgoi", 43.0083, 106.8500, "Mongolia"),
    Site("Cadia", -33.4667, 149.0000, "Australia"),
]

# Non-mineralized control sites (diverse land cover, geographically spread to avoid biasing
# the halo signature toward one region's non-deposit terrain).
TRAIN_NEGATIVE = [
    Site("Kansas wheat belt", 38.5000, -99.5000, "USA", "agricultural cropland"),
    Site("Black Forest", 48.3000, 8.2000, "Germany", "temperate forest"),
    Site("Nebraska Sand Hills", 42.0000, -101.5000, "USA", "grass-stabilized dunes, no mineralization"),
    Site("Pantanal wetlands", -17.5000, -57.0000, "Brazil", "wetland floodplain"),
    Site("Western Sahara erg", 24.0000, -10.0000, "Morocco/W. Sahara", "sand sea, non-mineralized"),
]

# Held out from training: known porphyry Cu(-Mo/Au) deposits worldwide, used only to check
# whether the halo signature re-identifies deposits it never trained on.
KNOWN_HOLDOUT = [
    Site("Morenci", 33.0500, -109.3667, "USA"),
    Site("Ray", 33.1717, -110.9878, "USA"),
    Site("Ajo / New Cornelia", 32.3717, -112.8608, "USA"),
    Site("Pebble", 59.9000, -155.0000, "USA", "undeveloped"),
    Site("Cananea", 30.9833, -110.3167, "Mexico"),
    Site("Andina", -33.1167, -70.2500, "Chile"),
    Site("Collahuasi", -20.9833, -68.6833, "Chile"),
    Site("Antamina", -9.5333, -77.0333, "Peru", "Cu-Zn skarn/porphyry"),
    Site("Batu Hijau", -8.9667, 116.8667, "Indonesia"),
    Site("Reko Diq", 28.9333, 62.6167, "Pakistan"),
    Site("Skouries", 40.5167, 23.7833, "Greece"),
    Site("Kalmakyr / Almalyk", 41.0167, 69.8500, "Uzbekistan"),
]


def training_set(name: str) -> list[Site]:
    return {"us5": TRAIN_POSITIVE_US5, "global12": TRAIN_POSITIVE_GLOBAL12}[name]
