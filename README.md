# nisar-tahoe-exploration: NISAR L-band SAR over Lake Tahoe

Exploratory analysis of NISAR GSLC (backscatter) and GUNW (interferogram) products over
Lake Tahoe (CA/NV). Goal: understand the data and build a reliable, georeferenced
visualization workflow. **No ML modelling at this stage.**

## Setup

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
# One-time Earthdata Login (prompts with hidden input, writes ~/.netrc with chmod 600):
.venv/bin/python setup_earthdata_auth.py
```

Catalog search needs no login; reading data does (verified: unauthenticated reads return HTTP 401).

**Getting the data:** `data/` holds GeoTIFF crops cut from the remote HDF5 products with GDAL.
See [`DATA_ACCESS.md`](DATA_ACCESS.md) for the GDAL setup, the exact commands, and known gotchas.

## Run

```bash
.venv/bin/python search_catalog.py   # -> outputs/scene_inventory_all.csv
.venv/bin/python run_eda.py          # -> GSLC β⁰ overview + GUNW coherence map/stats (from data/)
```

## Files

| File | Purpose |
|---|---|
| `search_catalog.py` | ASF catalog search over the Tahoe box, writes the scene inventory |
| `setup_earthdata_auth.py` | Local credential setup + 8-byte access test |
| `sar_utils.py` | Remote HDF5 streaming, metadata inspection (more helpers to come) |
| `outputs/scene_inventory_all.csv` | Every GSLC/GUNW/GCOV product intersecting the box, 2025–2026 |
| `outputs/scene_inventory_selected.csv` | The pair chosen for the first EDA |
| `docs/REPORT_initial_exploration.md` | Report of the initial exploration + questions for the mentor (2026-10-21) |
| `run_eda.py` | Analysis entry point: GSLC β⁰ overview maps/stats, GUNW coherence map/stats |
| `outputs/gunw_coherence_stats.csv` | Coherence percentiles for all / water / land (20 m, HH) |
| `outputs/figures/gunw_coherence_20251101_20251113.png` | Coherence map + land/water histograms |
| `outputs/gslc_change_stats.csv` | β⁰ change Nov 1 → Nov 13 (dB, 20 m) percentiles, HH and HV |
| `outputs/figures/gslc_change_20251101_20251113.png` | β⁰ change maps (HH, HV) next to the coherence map |
| `data/` | Local data (git-ignored) |

## Catalog findings (searched 2026-10-16)

Search box: W −120.3, S 38.8, E −119.8, N 39.3.

- **2025 coverage exists**: 21 GSLC, 21 GUNW, 21 GCOV products, all acquired Nov–Dec 2025.
  Each 2025 acquisition is available in two versions:
  - original **BETA** (CRID `X05009`/`X05010`), and
  - a **reprocessed PROVISIONAL** version (CRID `P05023`, collection `*_PROVISIONAL_V1`,
    product version 1.0.11).
- 2026: mostly PROVISIONAL `P05023`, plus a few products in an `NISAR_UR_L2` collection
  (maturity not stated in the collection name; not used).
- Stacks covering the box: track 34 ascending frame 21 and track 42 descending frame 69
  (footprint covers 100% of the box); track 106 ascending frames 21/22 (partial).
- File sizes: GSLC ≈ 22.7 GB, GCOV ≈ 7.1 GB, GUNW ≈ 2.3 GB, so we **stream subsets**
  rather than download whole files.

### Selected for the first EDA (2025 data, no substitution needed)

Track 42, descending, frame 69, PROVISIONAL `P05023`, frequency A 40 MHz, HH+HV:

| Role | Product |
|---|---|
| GSLC date 1 (2025-11-01) | `NISAR_L2_PR_GSLC_004_042_D_069_4005_DHDH_A_20251101T025606_20251101T025641_P05023_N_F_J_001` |
| GSLC date 2 (2025-11-13) | `NISAR_L2_PR_GSLC_005_042_D_069_4005_DHDH_A_20251113T025606_20251113T025641_P05023_N_F_J_001` |
| GUNW 11-01 → 11-13 (12-day, HH) | `NISAR_L2_PR_GUNW_004_042_D_069_005_4000_SH_20251101T025606_20251101T025641_20251113T025606_20251113T025641_P05023_N_F_J_001` |
| optional GCOV, same dates | `..._GCOV_004_..._20251101...` / `..._GCOV_005_..._20251113...` |

Rationale: same track, frame, direction, frequency, polarization, CRID and product version; the
earliest available 2025 dates (likely less snow than December). GUNW reference/secondary times
in the CMR metadata match the two GSLC acquisitions. Coverage was checked against the CMR
footprint and the public browse image; it will be re-checked against the HDF5 grid coordinates.

## Plan

1. ✅ Catalog search and inventory.
2. ⏳ Earthdata auth, then inspect the HDF5 structure of one GSLC and the GUNW (paths, shapes,
   dtypes, CRS, coordinates, fill values, masks).
3. Whole-lake crop → β⁰ (dB) map and coherence map. No study sub-area has been chosen yet.
   ✅ Whole-lake coherence map (2026-10-20): land median 0.85, water 0.19.
4. Both dates with shared colour limits; wrapped/unwrapped phase + connected components;
   histograms, valid-pixel fractions, percentiles; example patches.
   ✅ Both GSLC dates + β⁰ change map (2026-10-20): land ≈ unchanged, lake brighter in HH
   (wind). Phase layers and example patches still to do.
5. Notebook `tahoe_eda.ipynb` narrating the outputs; optional GCOV comparison.

## Sources and limitations

- NISAR docs: GSLC beta0 = |DN|² (no radiometric terrain flattening); GUNW is HH/VV, frequency A,
  12-day nearest-neighbour pairs; wrapped interferogram at 20 m, unwrapped phase at 80 m,
  coherence at both.
- PROVISIONAL = calibrated but only partially validated. VALIDATED reprocessing is expected
  late 2026 and will supersede these versions.
- Reference paper (forest height from L-band InSAR time series, Northern Spain): the full text
  returned HTTP 403 to automated access, so its methods have **not** been verified here.
