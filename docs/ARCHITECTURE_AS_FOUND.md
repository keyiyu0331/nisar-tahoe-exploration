# Geo-EDA: architecture as found

Snapshot written 2026-10-18 from a read-only pass over the project. Nothing was changed except
adding this file. Claims marked **(verified)** were checked against the files on disk (CSV
contents, GeoTIFF headers read with the project's own rasterio). Everything else comes from
reading the code and docs.

Project size: 4 Python files (~365 lines), 2 Markdown docs, 1 `requirements.txt`, 3 GeoTIFFs
(~415 MB), 1 browse PNG, 3 CSVs and 1 figure. Not a git repository, so the `.gitignore` has no
effect yet.

---

## 1. File by file

### `search_catalog.py` (86 lines)
Searches the ASF/CMR catalog for NISAR GSLC, GUNW and GCOV products whose footprint intersects a
hard-coded Lake Tahoe box `BBOX = (-120.3, 38.8, -119.8, 39.3)` (lon/lat, W S E N). It runs two
date ranges (`2025-01-01`–`2025-12-31T23:59:59Z`, and `2026-01-01`–open), so there are 3 × 2
`asf_search.search(...)` calls. Each result (`asf_search.ASFProduct`) goes through
`result_to_row(r, aoi: shapely.Polygon) -> dict`. That function flattens `r.properties`, plus the
CMR `AdditionalAttributes` (through `_attrs`), into 21 columns, adding `reference_start` and
`secondary_start` for GUNW. It also adds a derived `maturity` (from a substring of the collection
name, through `_maturity`), `aoi_covered_frac` (footprint ∩ box area divided by box area,
computed in degrees²) and `h5_size_GB`. `search_inventory() -> pd.DataFrame` de-duplicates on
`scene_name` and sorts. **Input:** network access to CMR, no login. **Output:**
`outputs/scene_inventory_all.csv` (320 rows × 23 columns **(verified)**), plus two group-by
summaries printed to stdout. **Called by:** a person, as a script. Nothing imports it.

### `setup_earthdata_auth.py` (57 lines)
A one-time credential helper. `has_entry() -> bool` checks `~/.netrc` for
`urs.earthdata.nasa.gov`. `write_entry()` prompts for a username and a hidden password, *appends*
a `machine/login/password` stanza to `~/.netrc`, then runs `chmod 600`. `test_access() -> bool`
imports `sar_utils.open_remote`, reads the first 8 bytes of the hard-coded GUNW URL (`TEST_URL`)
and compares them with the HDF5 signature `\x89HDF\r\n\x1a\n`. With `--test` it skips the write
step. **Inputs:** user typing, the file `~/.netrc`, the network. **Outputs:** an edited
`~/.netrc`, a message on stdout, exit code 0 or 1. **Called by:** a person, as a script. It is
the only caller of `sar_utils.open_remote`.

### `sar_utils.py` (143 lines)
The shared helper library, in four sections.
- *Access:* `open_remote(url, block_size=8 MiB)` returns a seekable file object. A local path
  goes through `open(..., "rb")`. An http(s) URL goes through an `fsspec` HTTPS filesystem with
  `aiohttp.BasicAuth` taken from `~/.netrc`, using `cache_type="blockcache"`.
  `open_h5(url) -> h5py.File` wraps `open_remote`.
- *Inspection:* `describe_h5(h5, root, max_depth, attrs) -> list[str]` makes one line per
  dataset, giving the shape, dtype, chunks and selected attributes.
- *Rasters:* `read_raster(path, bounds=None) -> (ndarray, Affine, CRS)` reads band 1, optionally
  only a window given in the raster's own CRS. `same_grid(*(transform, crs, shape)) -> bool`
  checks that grids match. `lonlat_to_crs(crs, lon, lat) -> (x, y)` converts coordinates with
  pyproj.
- *GSLC radiometry:* `gslc_valid(mask: uint8) -> bool array`, where valid means `0 < mask < 255`.
  `beta0_power(slc: complex64, valid) -> float32` returns |z|², with invalid pixels set to NaN.
  `power_to_db(p) -> float32`, where values that are not positive or not finite become NaN.
  `multilook(power, n, transform) -> (array (H//n, W//n), Affine)` takes a NaN-aware block mean in
  linear power, drops the remainder rows and columns, and scales the transform.
- *Stats and plotting:* `summary_stats(values, valid=None, pcts=...) -> dict` returns
  `n_pixels`, `valid_frac` and `p1…p99`, and deliberately no mean. `extent_km(transform, shape)`
  gives the extent for `imshow`, assuming a north-up raster. `plot_map(ax, arr, transform, crs,
  title, cbar_label, **kw)` draws `imshow` plus a colourbar.

**Called by:** `run_eda.py` (raster, radiometry and plot helpers) and `setup_earthdata_auth.py`
(`open_remote` only). `open_h5` and `describe_h5` have no caller in the repo.

### `run_eda.py` (79 lines)
The only analysis entry point. Its module-level constants act as the config: `GSLC_DATES =
["20251113"]`, `POLS = ["HH", "HV"]`, `LOOKS = 4`, fixed dB colour limits `DB_LIMITS`, four
`LANDMARKS` in lon/lat, and a proposed study patch (`SUBSET_CENTER`, `SUBSET_HALF_M = 5000`).
`load_gslc(date, pol, bounds=None) -> (beta0 float32 (8616, 5341), Affine, CRS)` reads
`data/gslc_{date}_freqA_{pol}.tif` and the matching mask, asserts that their grids are identical,
and returns the masked β⁰ power. `subset_bounds(crs) -> (l, b, r, t)` returns a 10 × 10 km box in
map metres around `SUBSET_CENTER`. `overview_maps(date) -> list[dict]`, for each polarisation:
- loads the full crop;
- computes `summary_stats` on the 5 m dB map, plus `mean_dB_of_linear` (the mean taken in linear
  power, then converted to dB);
- multilooks 4×4 to 20 m for display;
- plots the map with the fixed colour limits, overlays the landmarks and the subset rectangle;
- saves `outputs/figures/gslc_overview_{date}.png`.

`__main__` writes `outputs/gslc_stats.csv` (one row for each date and polarisation, 14 columns)
and prints the table. **Inputs:** the three GSLC GeoTIFFs. **Outputs:** one PNG and one CSV.
**Called by:** a person (`.venv/bin/python run_eda.py`), run from the project root because the
paths are relative. There is also a `__pycache__/run_eda.cpython-312.pyc`, which only appears
when the file is *imported*. So something (probably an interactive session or a notebook that no
longer exists) imported it as a module at 21:15 on Oct 16.

### `requirements.txt` (14 lines)
Lists the dependencies with no version pins, except `asf_search>=10.0`. The installed `.venv`
has asf_search 14.1.0, rasterio 1.5.2, h5py 3.16.0 and fsspec 2026.9.0, on Python 3.12.2 built
with uv from a miniconda base. It includes `jupyter`, `nbconvert` and `ipykernel`, which are
not used yet (the notebook is only planned). The GDAL command-line tools are *not* listed here.
They live in a separate conda env `gdal`, described in DATA_ACCESS.md.

### `README.md`
Covers the project goal (EDA only, no ML), setup, catalog findings, the selected product
pair/triple, a 5-step plan and a list of limitations. It is the human-readable record of a
decision that is not in code: which scenes were selected. Partly out of date (see §4).

### `DATA_ACCESS.md`
A runbook for the step the code does not do: cropping remote HDF5 products to local GeoTIFFs
with `gdal_translate -projwin` over `/vsicurl/`. Includes the zsh `GDAL_OPTS` array, the
hard-coded product URLs, the crop box (−120.1759, 38.8788, −119.8833, 39.2594), and loops for 3
GSLC layers and 7 GUNW layers. It also records the GSLC and GUNW mask encodings, a status table
(only GSLC 2025-11-13 is done), and an alignment rule (§8).

### `.gitignore`
Ignores `data/`, `.venv/`, `__pycache__/`, `.ipynb_checkpoints/`, `*.h5` and `.netrc`. It does
*not* ignore `outputs/`, so it looks as if the outputs were meant to be committed. The `.netrc`
line is a defensive belt-and-braces entry: the credentials file is written to `$HOME`, never
inside the project.

### Data and output artifacts
- `data/gslc_20251113_freqA_{HH,HV}.tif`: complex64, 5341 × 8616, 5 m, EPSG:32610, origin
  (743665, 4350195), deflate-compressed, 256² tiles, no nodata value set **(verified)**.
- `data/gslc_20251113_freqA_mask.tif`: uint8, same grid, nodata = 255 **(verified)**.
- `data/browse/gslc_20251101_latlon.png`: a 1999 × 1978 RGB browse image from ASF. No code reads
  it. The README says it was used to check coverage by eye.
- `outputs/scene_inventory_all.csv`: produced by `search_catalog.py`. Acquisitions span
  2025-11-01 → 2026-10-14.
- `outputs/scene_inventory_selected.csv`: 5 rows, the same columns as `_all` plus a leading
  `role` column. All 5 rows match rows in `_all` exactly **(verified)**. **No code produces it**,
  so it was curated by hand or in an interactive session that was not saved.
- `outputs/gslc_stats.csv`: 2 rows (HH and HV, 2025-11-13), `valid_frac = 1.0`, 46,018,056
  pixels each.
- `outputs/figures/gslc_overview_20251113.png`: a two-panel HH/HV β⁰ map at 20 m, with landmarks
  and the cyan subset box. It looks correct: the lake is dark, the landmarks sit on the shoreline.

---

## 2. Entry points and the end-to-end data path

There are four entry points: three Python scripts and one manual shell runbook.

```
[1] search_catalog.py            ASF CMR (no auth)
        └─► outputs/scene_inventory_all.csv
[ manual ] pick 5 rows ─► outputs/scene_inventory_selected.csv   (no code; rationale in README)
[ manual ] copy URLs by hand into DATA_ACCESS.md and setup_earthdata_auth.py
[2] setup_earthdata_auth.py      ─► ~/.netrc ; 8-byte HDF5 signature test via sar_utils.open_remote
[3] DATA_ACCESS.md shell blocks  (conda env "gdal", zsh)
        gdal_translate -projwin over HDF5:"/vsicurl/<url>"://science/LSAR/GSLC/grids/frequencyA/{HH,HV,mask}
        └─► data/gslc_<date>_freqA_<layer>.tif        (only 20251113 exists)
        (GUNW loop is documented, never run → no data/gunw_*.tif)
[4] run_eda.py
        read_raster(HH|HV) + read_raster(mask)            complex64 / uint8, (8616, 5341)
        → same_grid assert
        → gslc_valid(mask) → beta0_power = |z|², invalid→NaN   float32
        ├─► power_to_db → summary_stats (5 m, full crop) ┐
        ├─► nanmean(linear) → dB                         ├─► outputs/gslc_stats.csv
        └─► multilook 4×4 → dB → plot_map + overlays     └─► outputs/figures/gslc_overview_<date>.png
```

The "metrics" today are the per-polarisation percentiles, the valid fraction and the
linear-domain mean in `gslc_stats.csv`. There are no GUNW metrics (coherence, phase), no
second-date metrics and no subset metrics yet. The HDF5 streaming route in `sar_utils`
(`open_h5`, `describe_h5`) is a second way to get data that the current pipeline does not use.
GDAL replaced it for the actual data access.

---

## 3. Design decisions and how deliberate they look

| Decision | Evidence | Deliberate? |
|---|---|---|
| **Crop remote HDF5 to local GeoTIFF with the GDAL CLI**, rather than streaming HDF5 in Python | DATA_ACCESS.md explains why at length. `rasterio` was added to requirements at 21:12, at the same time as the TIFFs | **Deliberate, but a switch made mid-project.** `sar_utils`'s docstring still lists both routes, and the README still describes sar_utils as "Remote HDF5 streaming … (more helpers to come)". The h5py/fsspec route looks like the original plan that was overtaken. |
| **`gdal_translate -projwin`, not `gdalwarp`** | DATA_ACCESS §3: avoid resampling complex/phase data, keep the native grid | **Deliberate and well argued.** |
| **Crop the whole lake, cut the 10 km patch in Python later** | DATA_ACCESS §2 | Deliberate. But the Python cut has not been written (see §4). |
| **Config = module-level constants**; no YAML, CLI args or env vars | Every script | **Probably by default, not by choice.** It suits the current size. But the same AOI appears three different ways (search box, crop box, subset centre), and the product URLs are copied into two places (the shell runbook and the auth script) instead of being read from `scene_inventory_selected.csv`. |
| **File naming as an implicit schema**: `gslc_{date}_freqA_{layer}.tif` | It is produced by the shell loop and parsed by `run_eda.load_gslc` | Deliberate, but the contract is held together only by matching strings in two languages. |
| **Do radiometry in linear power; dB only for display and percentiles**; `summary_stats` leaves out the mean on purpose | Comments in `multilook`, `summary_stats`, `overview_maps` | **Deliberate and correct.** Percentiles do not change under a monotonic transform, so dB percentiles are valid. |
| **Fixed colour limits across dates** | `DB_LIMITS` comment | Deliberate (for comparing dates). The values were derived outside the code: "~2nd–98th percentiles of the 20 m maps", which no script computes. |
| **Validity from the product mask, not from the data** (no nodata set on the SLC TIFFs) | `gslc_valid`, the mask encoding in DATA_ACCESS | Deliberate. |
| **Separate environments**: uv `.venv` for Python, conda `gdal` for the CLI | README, DATA_ACCESS §1 | Deliberate (the HDF5 plugin problem). The side effect is two GDAL builds (rasterio's bundled one and the conda one), which could disagree. |
| **Credentials in `~/.netrc`, never in the repo** | auth script, `.gitignore` | Deliberate and careful. |
| **Outputs kept and committed, data ignored** | `.gitignore` | Probably deliberate, but moot until `git init`. |
| **Unpinned requirements** | `requirements.txt` | **Looks accidental.** The project's own reproducibility claim ("Reproducible EDA") rests on versions that are not recorded. |
| **No framework**: plain scripts + matplotlib (Agg), no package, no tests, no notebook | Whole repo | Deliberate for EDA. The planned notebook does not exist yet. |

---

## 4. Dead code, duplication, half-finished and suspicious items

**Dead code or unused paths**
- `sar_utils.open_h5` and `sar_utils.describe_h5` have no caller. `describe_h5`'s docstring says
  "Print…", but the function returns a list and prints nothing.
- The `bounds` argument of `run_eda.load_gslc` / `sar_utils.read_raster`, and therefore the whole
  window-reading branch, is never used with a value other than `None`.
- `summary_stats(valid=...)` is never passed.
- The `jupyter` / `nbconvert` / `ipykernel` dependencies serve a notebook that does not exist.
- `data/browse/gslc_20251101_latlon.png` is not referenced by any code.

**Duplication and copy-paste config**
- **Three AOIs, defined separately:** the search box (−120.3…−119.8, 38.8…39.3) in
  `search_catalog.py` and the README; the crop box (−120.1759…−119.8833, 38.8788…39.2594),
  typed twice in DATA_ACCESS.md loops; and `SUBSET_CENTER` in `run_eda.py`.
- **Product URLs repeated** in `setup_earthdata_auth.TEST_URL`, DATA_ACCESS.md (GSLC ×2, GUNW)
  and `scene_inventory_selected.csv`. The comment on `TEST_URL` says it comes "from
  outputs/scene_inventory_selected.csv", but it is pasted in by hand.
- `EDL_HOST` (sar_utils) and `HOST` (auth script) are the same constant, defined twice.
- `"South Lake Tahoe"` in `LANDMARKS` (−119.984, 38.939) and `SUBSET_CENTER` (−119.995, 38.925)
  are two slightly different points for the same idea.

**Half-finished**
- **The study subset is drawn but never cut.** DATA_ACCESS §2 says "The patch itself is cut in
  Python (`run_eda.py`)", and §8 says "`run_eda.py` snaps the study subset to multiples of 80 m
  from that origin". **Neither is true of the code.** `subset_bounds` has no snapping, and its
  result is only used to draw a rectangle. If the GUNW work starts on the assumption that §8 is
  already implemented, the 5/20/80 m layers will be silently misaligned.
- Only 1 of the 2 GSLC dates and 0 of the 7 GUNW layers have been downloaded. `GSLC_DATES` has
  one entry.
- README plan step 2 is still ⏳, although the GSLC was downloaded and checked. The README "Run"
  section lists only `search_catalog.py`. The Files table leaves out `run_eda.py` and
  `DATA_ACCESS.md`.
- The README's 2026 summary says "mostly PROVISIONAL plus a few NISAR_UR_L2". The CSV also has 4
  BETA GSLC and 4 BETA GCOV products in 2026 **(verified)**. Small, but the summary was written
  from a different run or by eye.
- The meaning of GUNW `connectedComponents = 0` is flagged in DATA_ACCESS as an assumption still
  to verify.

**Suspicious or fragile**
- **Hidden dependency coupling.** `sar_utils` imports `aiohttp`, `fsspec`, `h5py` and
  `matplotlib` at module level. So `run_eda` (which only needs rasterio) and the auth test (which
  only needs fsspec) both need the whole stack installed.
- **Relative paths.** `run_eda.py` and `search_catalog.py` use `Path("data")` / `Path("outputs")`
  and break if run from another directory. `setup_earthdata_auth.py` does handle this, through
  `__file__`, so the scripts are inconsistent with each other.
- **The Basic-Auth route to Earthdata.** `open_remote` sends `aiohttp.BasicAuth` to the ASF host.
  Earthdata normally answers with a redirect to `urs.earthdata.nasa.gov`, and HTTP clients often
  drop auth headers on a cross-host redirect. The README says unauthenticated reads give 401, but
  there is no record that `--test` *succeeded*. Worth confirming before anyone builds on
  `open_h5`.
- **`write_entry` appends.** If `~/.netrc` exists but does not parse, `has_entry()` returns
  False, and a second stanza is appended to a file that is already broken. The file is also
  created with the default umask and only then set to 600, which leaves a brief window. A
  password containing spaces or `#` would produce an invalid netrc.
- **`search_catalog.result_to_row`** assumes `p["bytes"]` is a dict and that every listed
  property key exists. A single odd CMR record would crash the whole search. `aoi_covered_frac`
  is an area ratio in degrees², which is fine as a fraction but not an area. `_maturity`'s
  substring match labels `NISAR_UR_L2` as `UNKNOWN`.
- **`multilook`** suppresses only `invalid` warnings. A block that is entirely NaN still emits a
  `RuntimeWarning: Mean of empty slice`. This is not visible today only because the mask is all
  1s.
- **`valid_frac = 1.0` over a crop that is ~40% lake.** This is correct for the GSLC mask (it
  marks swath validity, not water), but it means the "valid fraction" metric says nothing about
  land/water. A reader could misread it.
- **`DB_LIMITS` cannot be reproduced.** The comment describes a 20 m percentile computation that
  does not exist in the code. The CSV's percentiles are at 5 m, so they cannot be used to
  re-derive the limits.
- **Inherited GeoTIFF metadata.** DATA_ACCESS notes that the `min/max/mean_*_value` tags in the
  TIFFs describe the whole frame. Anything that reads these tags automatically will get the
  wrong numbers.
- The `__pycache__/run_eda.*.pyc` file points to an import-based session (a notebook or REPL)
  whose code is not in the project. This is also the most likely origin of
  `scene_inventory_selected.csv`.

---

## 5. Five questions for the original author

1. **How was `scene_inventory_selected.csv` produced, and what produced the `run_eda` import
   (`__pycache__`)?** Is there a notebook or REPL session with logic that is not in the repo
   (selection filters, the `DB_LIMITS` percentile computation)? If so, can it be recovered?
2. **DATA_ACCESS §8 describes the subset being snapped to the 80 m frame grid as if it were
   done in `run_eda.py`. Was that written ahead of the code on purpose, or did an implementation
   get lost?** Relatedly: do the GSLC, GUNW-20 m and GUNW-80 m grids really all share the origin
   (563760, 4446720), given that GSLC pixel edges sit at …665/…195?
3. **Is the Python HDF5-streaming route (`open_remote` → `open_h5` → `describe_h5`) abandoned
   in favour of GDAL, or kept for metadata inspection?** Did `setup_earthdata_auth.py --test`
   ever actually return "Access OK" through the aiohttp Basic-Auth path?
4. **Where should configuration live once there are two dates and GUNW layers?** Should the
   AOIs, product URLs and file-naming scheme come from one source (for example
   `scene_inventory_selected.csv` plus a small config file)? And can you pin the exact package
   and GDAL versions that produced the current outputs?
5. **What is the intended set of final "metrics", and over which region?** Right now the
   statistics cover the whole crop at 5 m. The plan mentions per-subset statistics, coherence,
   and land/water separation. Should statistics be split by a water mask (the GUNW mask's `W`
   digit, or an external one)? And should the shared colour limits be recomputed once the
   2025-11-01 date is added?
