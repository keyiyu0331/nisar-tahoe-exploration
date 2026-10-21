# Glossary

One plain sentence per term, plus where it shows up in this project. Figures are in `docs/figures/`.

## The instrument and the measurement

| Term | Meaning | Where in the code |
|---|---|---|
| **NISAR** | A NASA–ISRO radar satellite, launched 2025, that images almost all land on Earth every 12 days. | Every product name (`NISAR_L2_PR_...`) |
| **SAR** (synthetic aperture radar) | A radar that sends microwave pulses sideways at the ground and records the echoes, building an image that works day or night and through clouds. | Whole project |
| **L-band** | NISAR's main radar frequency, with a wavelength of about 24 cm, long enough to pass partly through tree canopies and snow. | `LSAR` in HDF5 paths |
| **Backscatter** | The fraction of the radar pulse that bounces back toward the satellite: smooth water sends little back (dark), rough or built-up surfaces send a lot back (bright). | `beta0_power`, the overview figure |
| **Polarization (HH, HV)** | The orientation of the radio wave sent and received: HH = sent horizontal, received horizontal; HV = sent horizontal, received vertical. HV is weaker and is especially sensitive to vegetation. | `POLS = ["HH", "HV"]` in `run_eda.py` |
| **Frequency A** | NISAR's main 20/40 MHz L-band channel (there is also a secondary "B" channel). | `freqA` in file names |

## One pixel

| Term | Meaning | Where in the code |
|---|---|---|
| **Complex pixel** | Each GSLC pixel is a complex number z = a + bj, i.e. an arrow with a length and an angle. | `complex64` dtype of `data/gslc_*_HH.tif` |
| **Amplitude** | The arrow's length \|z\|: how strong the echo was. | — |
| **Phase** | The arrow's angle: where in its wave cycle the echo arrived. Looks random within one image; meaningful when two dates are compared. | Used later in GUNW |
| **β⁰ (beta-nought)** | Echo power \|z\|² per pixel, NISAR's calibrated measure of backscatter brightness. "Not terrain-flattened" means slopes facing the radar still look extra bright. | `sar_utils.beta0_power` |
| **dB (decibels)** | 10·log₁₀(power); squashes a huge range of powers into a readable scale. Use only for display/percentiles, never for averaging. | `sar_utils.power_to_db` |
| **Mask** | A companion layer saying which pixels are valid (GSLC: `0` invalid, `1..n` valid, `255` outside the footprint). | `sar_utils.gslc_valid` |
| **Speckle** | The grainy salt-and-pepper look of SAR images, caused by many tiny echoes inside one pixel adding up with random phases. | Why `multilook` exists |

## Products and catalog

| Term | Meaning | Where in the code |
|---|---|---|
| **GSLC** | Geocoded Single-Look Complex: one date's complex image, already placed on a map grid (5 m pixels here). | `data/gslc_*.tif`, `run_eda.py` |
| **GUNW** | Geocoded Unwrapped Interferogram: the comparison of two dates' phases, showing ground motion and how much the surface changed. | `DATA_ACCESS.md` §7 (not downloaded yet) |
| **GCOV** | Geocoded covariance: power-only (no phase) product. Optional here. | `search_catalog.py` |
| **Track / frame** | Track = which repeating orbit path; frame = which slice along that path. Same track + frame on two dates = same viewing geometry. | `track 42, frame 69` in README |
| **Ascending / descending** | Whether the satellite was moving north or south during the pass; this changes which side of each mountain faces the radar. | `D` in product names |
| **Cycle / orbit number** | NISAR repeats its exact ground paths every 12 days (one cycle = 173 orbits). Cycle `004` → `005` and orbit 1352 → 1525 are one cycle apart. | `orbit` column, `_004_`/`_005_` in names |
| **Product level (L1 / L2)** | L1 products are in the radar's own geometry; L2 products are "geocoded", i.e. already resampled onto a map grid. This project uses only L2. | `NISAR_L2_...` in names |
| **Maturity (BETA / PROVISIONAL / VALIDATED)** | How well-checked a processing version is: BETA = early, PROVISIONAL = calibrated but partly validated, VALIDATED = final. | `_maturity`, `maturity` column |
| **CRID** | Code for the processing software version that made a product (e.g. `P05023`); same CRID on both dates = processed the same way. | `crid` column |
| **AOI / footprint** | AOI = the area you care about (the Tahoe box); footprint = the polygon a product actually covers on the ground. | `BBOX`, `aoi_covered_frac` |
| **WKT** | Well-Known Text: a string format for shapes, e.g. `POLYGON((-120.3 38.8, ...))`. | `aoi.wkt` in `search_catalog.py` |
| **ASF / CMR** | ASF = the NASA archive in Alaska that hosts NISAR data; CMR = NASA's searchable catalog of it. | `search_catalog.py` |
| **Earthdata Login** | Free NASA account required to read (not search) the data. | `setup_earthdata_auth.py`, `~/.netrc` |

## Files and maps

| Term | Meaning | Where in the code |
|---|---|---|
| **HDF5** | A file format that stores many named arrays in a folder-like tree inside one file (like a zip of NumPy arrays plus metadata). NISAR products are HDF5. | `sar_utils.open_h5`, `DATA_ACCESS.md` |
| **GeoTIFF** | An image file whose header also records where on Earth each pixel is. | `data/*.tif` |
| **CRS** (coordinate reference system) | The rulebook that turns numbers like (758005, 4329995) into a place on Earth. | `crs` returned by `read_raster` |
| **EPSG:4326** | The CRS of plain longitude/latitude in degrees. | `-projwin_srs EPSG:4326` |
| **UTM / EPSG:32610** | A flat-map CRS measured in metres (easting, northing); zone 10N covers Lake Tahoe. Used because pixels of fixed 5 m size need a metre grid. | Axis labels in the overview figure |
| **Transform (affine)** | Six numbers mapping (row, col) → (x, y): origin + pixel size. Here origin (743665, 4350195), 5 m pixels. | `rasterio` `Affine` objects |
| **~/.netrc** | A standard text file in your home folder that stores logins per host, read automatically by many tools (GDAL, curl, Python's `netrc`). | `setup_earthdata_auth.py`, `sar_utils.open_remote` |
| **HTTP range request** | Asking a web server for only bytes X–Y of a file instead of the whole file. This is what makes reading 200 MB out of a 23 GB file possible. | `open_remote`, GDAL `/vsicurl/` |
| **HDF5 signature** | The fixed first 8 bytes of every HDF5 file (`\x89HDF\r\n\x1a\n`), used as a cheap "is this really the file?" check. | `test_access` |

## Tools and data access (part 3)

| Term | Meaning | Where in the code |
|---|---|---|
| **Group / dataset / attribute (HDF5)** | Group = a folder inside the file; dataset = one N-D array; attribute = a small labelled value (units, fill value) attached to either. | `describe_h5`, HDF5 paths in `DATA_ACCESS.md` |
| **Chunk / tile** | Big arrays are stored in small blocks (e.g. 256 × 256 pixels), so a reader can fetch just the blocks it needs. | `chunks=` in `describe_h5`, `TILED=YES` |
| **GDAL** | The standard open-source library and command-line toolkit for reading/writing geospatial rasters; rasterio is a Python wrapper around it. | `DATA_ACCESS.md`, `rasterio` |
| **`/vsicurl/`** | GDAL's prefix for "read this URL as if it were a local file, using range requests". | `DATA_ACCESS.md` §5–7 |
| **`gdal_translate -projwin`** | Cut a rectangular window out of a raster **without changing its pixel grid**. | `DATA_ACCESS.md` §6 |
| **Resampling** | Computing new pixel values on a different grid by interpolating between old pixels (what `gdalwarp` does). Harmful to complex/phase data. | Avoided on purpose, `DATA_ACCESS.md` §3 |
| **Window** | A rectangular sub-region of a raster, given as row/column offsets and sizes. | `sar_utils.read_raster` |
| **Nodata / fill value** | A special value meaning "no measurement here" (e.g. 255 in the mask, NaN in GUNW layers). | Mask nodata = 255 |
| **pyproj / Transformer** | Python library that converts coordinates between CRSs, e.g. lon/lat → UTM metres. | `sar_utils.lonlat_to_crs` |

## Analysis (part 4)

| Term | Meaning | Where in the code |
|---|---|---|
| **Multilook** | Averaging power over n × n neighbouring pixels to reduce speckle, trading resolution (5 m → 20 m for n = 4) for a smoother image. Always done on power, never on complex values or dB. | `sar_utils.multilook`, `LOOKS = 4` |
| **Mean in linear vs dB** | Averaging power and then converting to dB is the physically correct mean; averaging dB values gives a different, biased number. Percentiles are the same either way. | `mean_dB_of_linear`, `summary_stats` |

## GUNW / interferometry

| Term | Meaning | Where in the code |
|---|---|---|
| **InSAR** | Interferometric SAR: comparing the phase of two SAR images of the same place from the same track to measure change. | GUNW product |
| **Interferogram** | Per-pixel phase difference Δφ between two dates (stored as a complex number whose angle is Δφ). | `wrappedInterferogram` layer |
| **Line of sight (LOS)** | The direction from the ground to the satellite; InSAR only measures motion along this direction. | — |
| **Wrapped phase** | Phase known only up to whole turns, always shown in −π…π; one full turn ≈ 12 cm of LOS motion at L-band. | `wrappedInterferogram` (20 m) |
| **Fringe** | One full colour cycle (2π) in a wrapped interferogram. | — |
| **Unwrapping / unwrapped phase** | Recovering the continuous phase by counting whole turns between neighbouring pixels; in radians. | `unwrappedPhase` (80 m) |
| **Coherence** | 0–1 score of how consistent Δφ is among neighbouring pixels, i.e. how much the ground's "random part" stayed the same between dates. Low coherence ⇒ phase is noise. | `coherenceMagnitude` (20 m and 80 m) |
| **Connected components** | Labels for regions that were unwrapped consistently with each other; offsets between different regions are unknown. 0 probably = not unwrapped (unverified). | `connectedComponents` (80 m) |

## Radiometric conventions

| Term | Meaning | Where in the code |
|---|---|---|
| **σ⁰ (sigma-nought)** | Backscatter power per unit ground area: σ⁰ = β⁰ · sin(θ). | — |
| **γ⁰ (gamma-nought)** | Backscatter power per unit area facing the beam: γ⁰ = β⁰ · tan(θ); reduces viewing-angle effects. | GCOV product (not used yet) |
| **Terrain flattening (RTC)** | Correcting backscatter with an elevation model so slopes facing the radar don't look bright just because of their tilt. GCOV γ⁰ is terrain-flattened; our GSLC β⁰ is not. | — |
| **L-band (name)** | Letter bands are WWII radar code names; "L" is often remembered as "Long". NISAR's L-band ≈ 1.25 GHz, ≈ 24 cm. | `LSAR` |
