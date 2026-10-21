"""Reproducible EDA for NISAR GSLC/GUNW over Lake Tahoe. Saves figures and tables to outputs/.

    .venv/bin/python run_eda.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import sar_utils as su

DATA, OUT = Path("data"), Path("outputs")
GSLC_DATES = ["20251101", "20251113"]
GUNW_PAIR = ("20251101", "20251113")  # reference, secondary
POLS = ["HH", "HV"]
LOOKS = 4  # display-only multilook: 4 x 4 pixels of 5 m -> 20 m
# Fixed colour limits (dB) so every date is shown on the same scale.
# Chosen as ~2nd-98th percentiles of the 20 m 2025-11-13 maps, rounded.
DB_LIMITS = {"HH": (-20, 2), "HV": (-26, -4)}

# Approximate town/landmark locations (lon, lat) for a visual georeferencing sanity check only
LANDMARKS = {"Tahoe City": (-120.145, 39.168), "Incline Village": (-119.952, 39.251),
             "South Lake Tahoe": (-119.984, 38.939), "Emerald Bay": (-120.105, 38.954)}


def load_gslc(date, pol, bounds=None):
    """Return (beta0 linear power, transform, crs) for one date/polarization, masked."""
    slc, t, crs = su.read_raster(DATA / f"gslc_{date}_freqA_{pol}.tif", bounds)
    mask, tm, cm = su.read_raster(DATA / f"gslc_{date}_freqA_mask.tif", bounds)
    assert su.same_grid((t, crs, slc.shape), (tm, cm, mask.shape)), "SLC and mask grids differ"
    return su.beta0_power(slc, su.gslc_valid(mask)), t, crs


def add_overlays(ax, crs):
    """Landmarks on a map in km of `crs`: black-ringed dots, bold labels on a white box so they
    stay readable on grey, red and blue backgrounds."""
    for name, (lon, lat) in LANDMARKS.items():
        x, y = su.lonlat_to_crs(crs, lon, lat)
        ax.plot(x / 1000, y / 1000, "o", ms=6, mfc="white", mec="black", mew=1.5)
        ax.annotate(name, (x / 1000, y / 1000), xytext=(5, 5), textcoords="offset points",
                    color="black", fontsize=8, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))


def overview_maps(date):
    """Whole-lake crop, HH and HV beta0 (dB), with landmarks."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 9), constrained_layout=True)
    rows = []
    for ax, pol in zip(axes, POLS):
        p, t, crs = load_gslc(date, pol)
        rows.append({"date": date, "pol": pol, "region": "whole crop", "resolution_m": 5,
                     **su.summary_stats(su.power_to_db(p)),
                     # spatial mean taken in linear power, then converted to dB
                     "mean_dB_of_linear": float(su.power_to_db(np.nanmean(p, keepdims=True))[0, 0])})
        p_ml, t_ml = su.multilook(p, LOOKS, t)
        su.plot_map(ax, su.power_to_db(p_ml), t_ml, crs,
                    f"GSLC β⁰ {pol}, {date} ({5 * LOOKS} m multilook)", "β⁰ (dB)",
                    cmap="gray", vmin=DB_LIMITS[pol][0], vmax=DB_LIMITS[pol][1])
        add_overlays(ax, crs)
    fig.suptitle("NISAR GSLC β⁰ (beta-nought, not terrain-flattened), track 42 descending, frame 69\n"
                 "labelled dots: approximate landmark positions")
    fig.savefig(OUT / "figures" / f"gslc_overview_{date}.png", dpi=130)
    plt.close(fig)
    return rows


def coherence_maps(ref, sec):
    """GUNW 20 m HH coherence: map plus land/water histograms, and per-region stats."""
    stem = DATA / f"gunw_{ref}_{sec}"
    coh, t, crs = su.read_raster(f"{stem}_coherence_20m.tif")
    mask, tm, cm = su.read_raster(f"{stem}_mask_20m.tif")
    assert su.same_grid((t, crs, coh.shape), (tm, cm, mask.shape)), "coherence and mask grids differ"
    valid, water = su.gunw_mask_decode(mask)
    regions = {"all": valid, "water": water, "land": valid & ~water}
    # valid_frac below = fraction of the crop in that region
    rows = [{"pair": f"{ref}_{sec}", "pol": "HH", "region": name, "resolution_m": 20,
             **su.summary_stats(coh, valid=sel)}
            for name, sel in regions.items()]

    fig, (ax_map, ax_hist) = plt.subplots(1, 2, figsize=(13, 8), constrained_layout=True,
                                          gridspec_kw={"width_ratios": [1.1, 1]})
    # coherence is already a windowed estimate, so no multilook; fixed 0-1 scale for every pair
    su.plot_map(ax_map, np.where(valid, coh, np.nan), t, crs,
                f"GUNW coherence HH, {ref} → {sec} (20 m)", "coherence", cmap="gray", vmin=0, vmax=1)
    add_overlays(ax_map, crs)
    bins = np.linspace(0, 1, 51)
    for name, color in [("water", "#2a78d6"), ("land", "#eb6834")]:
        v = coh[regions[name] & np.isfinite(coh)]
        ax_hist.hist(v, bins=bins, density=True, histtype="step", lw=2, color=color,
                     label=f"{name} ({regions[name].mean():.0%} of pixels, median {np.median(v):.2f})")
    ax_hist.set_xlabel("coherence"); ax_hist.set_ylabel("density")
    ax_hist.set_title("Coherence by surface type (water flag from the GUNW mask)", fontsize=10)
    ax_hist.legend(frameon=False)
    ax_hist.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"NISAR GUNW coherence, track 42 descending, frame 69: {ref} → {sec} (12 days)\n"
                 "1 = surface unchanged, phase trustworthy; 0 = surface changed, phase is noise")
    fig.savefig(OUT / "figures" / f"gunw_coherence_{ref}_{sec}.png", dpi=130)
    plt.close(fig)
    return rows


def change_maps(ref, sec):
    """beta0 change sec vs ref (dB) for HH and HV at 20 m, next to the GUNW coherence map."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 8.5), constrained_layout=True)
    rows = []
    for ax, pol in zip(axes, POLS):
        p_ref, t, crs = load_gslc(ref, pol)
        p_sec, t2, crs2 = load_gslc(sec, pol)
        assert su.same_grid((t, crs, p_ref.shape), (t2, crs2, p_sec.shape)), "dates on different grids"
        rows.append({"ref": ref, "sec": sec, "pol": pol, "region": "whole crop",
                     # change of the spatial means, both taken in linear power
                     "change_of_means_dB": float(10 * np.log10(np.nanmean(p_sec) / np.nanmean(p_ref)))})
        # multilook before comparing: a 5 m per-pixel ratio is dominated by speckle
        ml_ref, t_ml = su.multilook(p_ref, LOOKS, t)
        ml_sec, _ = su.multilook(p_sec, LOOKS, t)
        del p_ref, p_sec
        change = su.power_to_db(ml_sec) - su.power_to_db(ml_ref)
        rows[-1].update({"resolution_m": 5 * LOOKS, **su.summary_stats(change)})
        su.plot_map(ax, change, t_ml, crs, f"β⁰ change {pol}, {ref} → {sec} ({5 * LOOKS} m)",
                    "change (dB): red = brighter on 2nd date", cmap="RdBu_r", vmin=-6, vmax=6)
        add_overlays(ax, crs)
    # coherence for side-by-side reading only: its 20 m grid is offset 5 m from the GSLC multilook grid
    coh, tc, cc = su.read_raster(DATA / f"gunw_{ref}_{sec}_coherence_20m.tif")
    valid, _ = su.gunw_mask_decode(su.read_raster(DATA / f"gunw_{ref}_{sec}_mask_20m.tif")[0])
    su.plot_map(axes[2], np.where(valid, coh, np.nan), tc, cc, f"GUNW coherence HH, {ref} → {sec} (20 m)",
                "coherence", cmap="gray", vmin=0, vmax=1)
    add_overlays(axes[2], cc)
    fig.suptitle(f"What changed between {ref} and {sec}? Brightness change (left, middle) vs coherence (right)\n"
                 "β⁰ not terrain-flattened; changes over the lake are wind and noise")
    fig.savefig(OUT / "figures" / f"gslc_change_{ref}_{sec}.png", dpi=130)
    plt.close(fig)
    return rows


if __name__ == "__main__":
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    stats = []
    for d in GSLC_DATES:
        stats += overview_maps(d)
    pd.DataFrame(stats).round(3).to_csv(OUT / "gslc_stats.csv", index=False)
    print(pd.DataFrame(stats).round(2).to_string())
    coh_stats = pd.DataFrame(coherence_maps(*GUNW_PAIR)).round(3)
    coh_stats.to_csv(OUT / "gunw_coherence_stats.csv", index=False)
    print(coh_stats.to_string())
    chg_stats = pd.DataFrame(change_maps(*GUNW_PAIR)).round(3)
    chg_stats.to_csv(OUT / "gslc_change_stats.csv", index=False)
    print(chg_stats.to_string())
