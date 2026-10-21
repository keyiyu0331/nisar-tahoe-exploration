"""Search the ASF catalog for NISAR GSLC/GUNW/GCOV over Lake Tahoe and save a scene inventory.

Metadata-only: no Earthdata Login needed.

    python search_catalog.py            # writes outputs/scene_inventory_all.csv
"""
from pathlib import Path

import asf_search as asf
import pandas as pd
from shapely.geometry import box, shape

# Approximate Lake Tahoe search box (lon/lat, EPSG:4326)
BBOX = (-120.3, 38.8, -119.8, 39.3)  # west, south, east, north
DATE_RANGES = [("2025-01-01", "2025-12-31T23:59:59Z"), ("2026-01-01", None)]
PRODUCTS = ["GSLC", "GUNW", "GCOV"]
OUT = Path("outputs")


def _attrs(result):
    """Flatten CMR AdditionalAttributes into a dict of comma-joined strings."""
    return {a["Name"]: ",".join(a["Values"]) for a in result.umm.get("AdditionalAttributes", [])}


def _maturity(collection):
    for m in ("VALIDATED", "PROVISIONAL", "BETA"):
        if m in collection:
            return m
    return "UNKNOWN"


def result_to_row(r, aoi):
    p, a = r.properties, _attrs(r)
    footprint = shape(r.geometry)
    h5 = p["bytes"].get(p["fileName"], {}).get("bytes")
    row = {
        "product": p["processingLevel"],
        "scene_name": p["sceneName"],
        "start_time": p["startTime"],
        "stop_time": p["stopTime"],
        "track": p["pathNumber"],
        "frame": p["frameNumber"],
        "direction": p["flightDirection"],
        "orbit": p["orbit"],
        "frequencies": a.get("FREQUENCIES"),
        "freqA_pols": a.get("FREQUENCY_A_POLARIZATION_CONCAT"),
        "freqB_pols": a.get("FREQUENCY_B_POLARIZATION_CONCAT"),
        "range_bandwidth_MHz": a.get("RANGE_BANDWIDTH_CONCAT"),
        "maturity": _maturity(p["collectionName"]),
        "collection": p["collectionName"],
        "crid": p["crid"],
        "pge_version": p["pgeVersion"],
        "product_version": a.get("PRODUCT_VERSION"),
        "frame_coverage": p["frameCoverage"],
        # Fraction of the search box inside the product footprint (footprint is approximate).
        "aoi_covered_frac": round(footprint.intersection(aoi).area / aoi.area, 3),
        "h5_size_GB": round(h5 / 1e9, 2) if h5 else None,
        "url": p["url"],
    }
    if p["processingLevel"] == "GUNW":
        row["reference_start"] = a.get("REFERENCE_ZERO_DOPPLER_START_TIME")
        row["secondary_start"] = a.get("SECONDARY_ZERO_DOPPLER_START_TIME")
    return row


def search_inventory():
    aoi = box(*BBOX)
    rows = []
    for product in PRODUCTS:
        for start, end in DATE_RANGES:
            results = asf.search(dataset="NISAR", processingLevel=product,
                                 intersectsWith=aoi.wkt, start=start, end=end)
            rows += [result_to_row(r, aoi) for r in results]
    df = pd.DataFrame(rows).drop_duplicates("scene_name")
    return df.sort_values(["product", "start_time", "track", "crid"]).reset_index(drop=True)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    df = search_inventory()
    df.to_csv(OUT / "scene_inventory_all.csv", index=False)
    print(f"{len(df)} products -> {OUT / 'scene_inventory_all.csv'}")
    df["year"] = df.start_time.str[:4]
    print(df.groupby(["product", "year", "maturity", "crid"]).size().to_string())
    print(df.groupby(["product", "track", "direction", "frame"]).agg(
        n=("scene_name", "size"), cover=("aoi_covered_frac", "max")).to_string())
