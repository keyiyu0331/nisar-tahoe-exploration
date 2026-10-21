# Data access: cropping NISAR products with GDAL

How the files in `data/` were produced. Full NISAR products are large (GSLC ≈ 23 GB,
GUNW ≈ 2.3 GB), so we never download whole files. GDAL reads the remote HDF5 over HTTPS
(`/vsicurl/`), fetches only the internal blocks covering our region, and writes a GeoTIFF.

Product choice and the full scene list are in `README.md` and `outputs/scene_inventory_*.csv`.

## Status

| Product | Date(s) | Layers | Status |
|---|---|---|---|
| GSLC | 2025-11-13 | freqA HH, HV, mask | ✅ downloaded and checked (2026-10-16) |
| GSLC | 2025-11-01 | freqA HH, HV, mask | ✅ downloaded and checked (2026-10-20) |
| GUNW | 2025-11-01 → 2025-11-13 | 7 layers (below) | ✅ downloaded and checked (2026-10-20) |

## 1. One-time setup

### Earthdata Login credentials

Reading NISAR data requires a free NASA Earthdata account (https://urs.earthdata.nasa.gov).
Unauthenticated reads fail with HTTP 401. Store credentials in `~/.netrc` (home folder, never in
this project) with:

```bash
cd ~/Desktop/Geo-EDA && .venv/bin/python setup_earthdata_auth.py
```

It prompts for the password with hidden input, writes the entry below with permissions 600, and
test-reads 8 bytes of the GUNW file:

```
machine urs.earthdata.nasa.gov
    login <USERNAME>
    password <PASSWORD>
```

### GDAL command-line tools

Installed in a separate conda environment named `gdal`, kept apart from the project `.venv`:

```bash
conda create -n gdal -c conda-forge gdal -y
conda install -n gdal -c conda-forge libgdal-hdf5 -y   # REQUIRED: HDF5 driver is a separate plugin
conda activate gdal
gdalinfo --formats | grep -i hdf5                      # must list "HDF5" and "HDF5Image"
```

Gotcha: the plain `gdal` package (3.13.3 at the time) did **not** include the HDF5 driver.
Without `libgdal-hdf5`, the `grep` prints nothing and the commands below fail.

## 2. Region of interest

Whole-lake box (WGS84 lon/lat), drawn in the ASF Data Search portal:

| West | East | South | North |
|---|---|---|---|
| −120.1759 | −119.8833 | 38.8788 | 39.2594 |

Gotcha: the portal's snippet gave longitudes like `-480.1759`, because the map had wrapped around
the globe. Add 360 to get the real longitude (−480.1759 + 360 = −120.1759). GDAL takes −480
literally and finds no overlap.

We crop the whole lake, so any smaller study area chosen later can be cut in Python without
downloading again. No study area has been chosen yet.

## 3. Why `gdal_translate`, not the portal's `gdalwarp` snippet

The ASF portal suggests `gdalwarp ... -cutline ... -crop_to_cutline -dstalpha`. We use
`gdal_translate -projwin` instead because:

- `gdalwarp` **resamples** onto a new grid. SLC and interferogram pixels are complex values that
  carry phase, which should not be resampled during download.
- `gdal_translate -projwin` cuts a window out of the **original pixel grid** and keeps the values
  unchanged. Verified: the GSLC crop origin is offset from the frame origin by whole pixels.
- `-dstalpha` would add an extra alpha band, which we don't need.

`-projwin_srs EPSG:4326` lets us give the window in lon/lat. GDAL converts it to the product's
CRS (UTM zone 10N) and takes the enclosing rectangle, so the crop is slightly larger than the
lon/lat box.

## 4. Common options (paste first in each session)

```bash
setopt interactivecomments
conda activate gdal
cd ~/Desktop/Geo-EDA

GDAL_OPTS=(
  --config GDAL_HTTP_NETRC YES
  --config GDAL_HTTP_COOKIEFILE /tmp/gdal_cookies.txt
  --config GDAL_HTTP_COOKIEJAR /tmp/gdal_cookies.txt
  --config GDAL_DISABLE_READDIR_ON_OPEN TRUE
  --config CPL_VSIL_CURL_CHUNK_SIZE 2097152
  --config CPL_VSIL_CURL_CACHE_SIZE 1GB
  --config GDAL_HTTP_MERGE_CONSECUTIVE_RANGES YES
  --config GDAL_HTTP_MULTIPLEX YES
)
```

| Option | Purpose |
|---|---|
| `GDAL_HTTP_NETRC` | use `~/.netrc` for Earthdata Login |
| `GDAL_HTTP_COOKIEFILE` / `COOKIEJAR` | read and save the login cookie, to avoid logging in again on every request |
| `GDAL_DISABLE_READDIR_ON_OPEN` | don't try to list the remote "directory" |
| `CPL_VSIL_CURL_CHUNK_SIZE` | 2 MB HTTP range requests |
| `CPL_VSIL_CURL_CACHE_SIZE` | keep up to 1 GB of fetched blocks in memory |
| `GDAL_HTTP_MERGE_CONSECUTIVE_RANGES`, `GDAL_HTTP_MULTIPLEX` | fewer, more efficient HTTP requests |

Gotchas (zsh, the macOS default shell):

- Keep the options in an **array** `( ... )` and expand them as `"${GDAL_OPTS[@]}"`. A plain string
  `GDAL_OPTS="..."` is not split into separate words by zsh, so GDAL would receive one broken argument.
- Without `setopt interactivecomments`, an interactive zsh treats `#` as ordinary text, not a comment.
  Comment lines in pasted blocks then give "command not found: #", and a comment *inside* an array
  silently becomes extra arguments. The `setopt` line fixes this for the current terminal session.

## 5. Inspect before downloading (metadata only, takes seconds)

One layer: check CRS, origin, pixel size, data type, fill value:

```bash
gdalinfo "${GDAL_OPTS[@]}" "HDF5:\"/vsicurl/$URL\"://science/LSAR/GSLC/grids/frequencyA/HH"
```

List all layers in a file: use the plain `/vsicurl/` path. `HDF5:"..."` without a layer path fails
with "No such file or directory".

```bash
gdalinfo "${GDAL_OPTS[@]}" "/vsicurl/$URL" | grep SUBDATASET_.*_DESC
```

## 6. GSLC crops (frequency A: HH, HV, mask)

```bash
# 2025-11-13  (done)
DATE=20251113
URL="https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GSLC_PROVISIONAL_V1/NISAR_L2_PR_GSLC_005_042_D_069_4005_DHDH_A_20251113T025606_20251113T025641_P05023_N_F_J_001/NISAR_L2_PR_GSLC_005_042_D_069_4005_DHDH_A_20251113T025606_20251113T025641_P05023_N_F_J_001.h5"

# 2025-11-01  (done: swap these two lines in, then rerun the loop)
# DATE=20251101
# URL="https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GSLC_PROVISIONAL_V1/NISAR_L2_PR_GSLC_004_042_D_069_4005_DHDH_A_20251101T025606_20251101T025641_P05023_N_F_J_001/NISAR_L2_PR_GSLC_004_042_D_069_4005_DHDH_A_20251101T025606_20251101T025641_P05023_N_F_J_001.h5"

for LAYER in HH HV mask; do
  echo "=== $LAYER ==="
  gdal_translate "${GDAL_OPTS[@]}" \
    -projwin_srs EPSG:4326 -projwin -120.1759 39.2594 -119.8833 38.8788 \
    -co COMPRESS=DEFLATE -co TILED=YES \
    "HDF5:\"/vsicurl/$URL\"://science/LSAR/GSLC/grids/frequencyA/$LAYER" \
    "data/gslc_${DATE}_freqA_${LAYER}.tif"
done
ls -lh data/*.tif
```

`-projwin` order: upper-left x y (west north), then lower-right x y (east south).

Result for 2025-11-13 (verified):

| File | Size | Type | Notes |
|---|---|---|---|
| `gslc_20251113_freqA_HH.tif` | 208 MB | complex64 | 5341 × 8616 px, 5 m, EPSG:32610 |
| `gslc_20251113_freqA_HV.tif` | 207 MB | complex64 | same grid |
| `gslc_20251113_freqA_mask.tif` | 73 KB | uint8 | same grid; all pixels = 1 in this crop |

All three: origin (743665, 4350195) m, pixel size 5 m × 5 m.

2025-11-01 (verified 2026-10-20): same file sizes, and all six GSLC files (both dates × HH, HV,
mask) are on the **identical** grid (`sar_utils.same_grid` → True), so the two dates can be compared
pixel by pixel. Nov 1 mask is also all `1`. Whole-crop median β⁰: HH −13.3 dB (Nov 1) vs −12.6 dB
(Nov 13); HV −18.6 vs −18.4 dB.

GSLC mask values (from the file's own description): `0` = invalid or partially focused,
`1..n` = valid (subswath number), `255` = outside the radar footprint (fill).

Gotcha: the `min/max/mean_*_value` items in the GeoTIFF metadata were copied from the
original HDF5 attributes and describe the **whole frame**, not the crop.

## 7. GUNW crops (2025-11-01 → 2025-11-13, HH)

The GUNW has **two grids**. Both are UTM 10N and share the frame origin (563760, 4446720):

| Group | Pixel | Full size | Layers we crop |
|---|---|---|---|
| `wrappedInterferogram` | 20 m | 17244 × 17496 | wrapped interferogram (complex), coherence, mask |
| `unwrappedInterferogram` | 80 m | 4311 × 4374 | unwrapped phase (radians), coherence, connected components, mask |

```bash
URL="https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GUNW_PROVISIONAL_V1/NISAR_L2_PR_GUNW_004_042_D_069_005_4000_SH_20251101T025606_20251101T025641_20251113T025606_20251113T025641_P05023_N_F_J_001/NISAR_L2_PR_GUNW_004_042_D_069_005_4000_SH_20251101T025606_20251101T025641_20251113T025606_20251113T025641_P05023_N_F_J_001.h5"
GRP=//science/LSAR/GUNW/grids/frequencyA

# layer path inside the file          -> short output name
LAYERS=(
  wrappedInterferogram/HH/wrappedInterferogram   wrapped_20m
  wrappedInterferogram/HH/coherenceMagnitude     coherence_20m
  wrappedInterferogram/mask                      mask_20m
  unwrappedInterferogram/HH/unwrappedPhase       unwrapped_80m
  unwrappedInterferogram/HH/coherenceMagnitude   coherence_80m
  unwrappedInterferogram/HH/connectedComponents  conncomp_80m
  unwrappedInterferogram/mask                    mask_80m
)

for ((i = 1; i <= ${#LAYERS[@]}; i += 2)); do
  LAYER=${LAYERS[i]}; NAME=${LAYERS[i+1]}
  echo "=== $NAME ==="
  gdal_translate "${GDAL_OPTS[@]}" \
    -projwin_srs EPSG:4326 -projwin -120.1759 39.2594 -119.8833 38.8788 \
    -co COMPRESS=DEFLATE -co TILED=YES \
    "HDF5:\"/vsicurl/$URL\":$GRP/$LAYER" \
    "data/gunw_20251101_20251113_${NAME}.tif"
done
ls -lh data/gunw_*.tif
```

(The `for ((i = 1; ...))` loop uses zsh's 1-based array indexing.)

Result (verified 2026-10-20, same crop box as the GSLC):

| File (`data/gunw_20251101_20251113_*`) | Size | Type | Grid | Values in the crop |
|---|---|---|---|---|
| `wrapped_20m.tif` | 20 MB | complex64 | 1336 × 2155 px, 20 m | no NaN or zeros; no nodata set |
| `coherence_20m.tif` | 9.5 MB | float32 | same 20 m grid | 0.004–0.998, median 0.70 |
| `mask_20m.tif` | 47 KB | uint32 | same 20 m grid | `11` (land) 56 %, `111` (water) 44 % |
| `unwrapped_80m.tif` | 608 KB | float32 | 335 × 540 px, 80 m | −20.6 … 5.3 rad, median −7.8 |
| `coherence_80m.tif` | 623 KB | float32 | same 80 m grid | 0.006–0.981, median 0.73 |
| `conncomp_80m.tif` | 6 KB | uint16 | same 80 m grid | `1` 57 %, `0` 43 % |
| `mask_80m.tif` | 11 KB | uint32 | same 80 m grid | see note below |

Origins: 20 m grid (743660, 4350200); 80 m grid (743600, 4350240); GSLC 5 m grid (743665, 4350195).
All three sit a whole number of pixels from the frame origin, but they start at **different corners**
(see §8). CRS EPSG:32610 for all.

Findings:
- Connected component `0` matches the mask's water flag on 98.7 % of 80 m pixels, which supports
  "0 = not unwrapped (water excluded)". Still not confirmed by documentation.
- The 80 m mask has low-byte codes `12` and `124` (and bit 24 set on most pixels), unlike the 20 m
  mask's `11` / `111`. By the `W R S` reading, `12` would mean "secondary subswath 2". Not yet
  understood; check the product specification before using the 80 m mask's subswath digits.

Layer metadata, read with `gdalinfo` before downloading:

| Layer | Units | Fill / NoData |
|---|---|---|
| unwrappedPhase | radians | NaN |
| coherenceMagnitude (20 m and 80 m) | unitless, 0–1 | NaN |
| connectedComponents | label | 65535 |
| wrappedInterferogram | complex | not stated; check after download |
| mask (20 m and 80 m) | bit-packed uint32 | 255 |

GUNW mask encoding (from the file's description):

- **Bits 0–7** hold a 3-digit decimal code `W R S`:
  - `W` = water flag in the reference image (1 = water).
  - `R` = subswath number in the reference image (first date).
  - `S` = subswath number in the secondary image (second date).
  - `R` or `S` = 0 means invalid in that image. Example: `11` = land, valid in both; `111` = water, valid in both.
- **Bits 8–15:** anomaly flags for the secondary image.
- **Bits 16–23:** anomaly flags for the reference image. 0 means no anomaly.
- **Bit 24:** ionospheric-filter mask.

The meaning of connected component `0` is not stated in the metadata. The common convention is
"not reliably unwrapped", but this is an assumption still to verify.

## 8. Alignment note

Each crop has its own origin, because different grids are cut at the nearest pixel edges. The
GSLC (5 m) and GUNW (20 m, 80 m) crops therefore do **not** start at the same corner, even though
they cover the same area. Every grid sits a whole number of pixels from the frame origin
(563760, 4446720), so any region snapped to multiples of 80 m from that origin lines up exactly in
the 5, 20 and 80 m layers. **This snapping is not implemented yet**: the current maps are shown side
by side, each georeferenced by its own transform, and never combined pixel by pixel. Implement and
check it before overlaying, differencing or stacking layers from different grids.
