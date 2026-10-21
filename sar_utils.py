"""Reusable helpers for NISAR GSLC / GUNW / GCOV exploratory analysis.

Two input routes:
- GeoTIFF crops made with gdal_translate (see README), read with rasterio.
- Remote HDF5 streamed over HTTPS with byte-range requests (open_h5), using
  Earthdata credentials from ~/.netrc (see setup_earthdata_auth.py).
"""
import netrc

import aiohttp
import fsspec
import h5py
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds

EDL_HOST = "urs.earthdata.nasa.gov"


# ---------------------------------------------------------------- access

def open_remote(url, block_size=8 * 1024 * 1024):
    """Return a seekable file object for an ASF HTTPS URL (or a local path)."""
    if not str(url).startswith("http"):
        return open(url, "rb")
    auth = netrc.netrc().authenticators(EDL_HOST)
    if auth is None:
        raise RuntimeError(f"No {EDL_HOST} entry in ~/.netrc; run setup_earthdata_auth.py")
    login, _, password = auth
    fs = fsspec.filesystem("https", client_kwargs={"auth": aiohttp.BasicAuth(login, password)})
    # 'blockcache' keeps recently read blocks so repeated metadata reads are cheap
    return fs.open(url, block_size=block_size, cache_type="blockcache")


def open_h5(url):
    return h5py.File(open_remote(url), "r")


# ---------------------------------------------------------------- inspection

def describe_h5(h5, root="/", max_depth=8, attrs=("units", "description", "_FillValue", "long_name")):
    """Print every dataset under `root` with shape, dtype, and selected attributes."""
    lines = []

    def visit(name, obj):
        if name.count("/") >= max_depth or not isinstance(obj, h5py.Dataset):
            return
        meta = {}
        for k in attrs:
            if k in obj.attrs:
                v = obj.attrs[k]
                v = v.decode() if isinstance(v, bytes) else v
                meta[k] = str(v)[:70]
        lines.append(f"{obj.name}  shape={obj.shape} dtype={obj.dtype} chunks={obj.chunks} {meta}")

    h5[root].visititems(visit)
    return lines


# ---------------------------------------------------------------- rasters (GeoTIFF crops)

def read_raster(path, bounds=None):
    """Read band 1, optionally only the window inside `bounds` (left, bottom, right, top)
    given in the raster's own CRS. Returns (array, transform, crs)."""
    with rasterio.open(path) as src:
        window = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths() if bounds else None
        arr = src.read(1, window=window)
        transform = src.window_transform(window) if window else src.transform
        return arr, transform, src.crs


def same_grid(*grids):
    """True if all (transform, crs, shape) tuples describe the identical pixel grid."""
    t0, c0, s0 = grids[0]
    return all(t == t0 and c == c0 and s == s0 for t, c, s in grids[1:])


def lonlat_to_crs(crs, lon, lat):
    return Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(lon, lat)


# ---------------------------------------------------------------- GSLC backscatter

def gslc_valid(mask):
    """GSLC freqA mask: 0 = invalid/partially focused, 1..n = valid subswath, 255 = outside swath."""
    return (mask > 0) & (mask < 255)


def gunw_mask_decode(mask):
    """GUNW mask (uint32): bits 0-7 hold a decimal code 'W R S' (water flag, reference and
    secondary subswath; 0 = invalid), 255 = fill. Returns (valid, water) bool arrays.
    Checked on the 20 m mask only; the 80 m mask's codes (12, 124) are not yet understood."""
    low = mask & 0xFF
    valid = (mask != 255) & ((low // 10) % 10 > 0) & (low % 10 > 0)
    return valid, valid & (low // 100 == 1)


def beta0_power(slc, valid):
    """Linear beta-nought power |z|^2 (NISAR GSLC docs: beta0 = |DN|^2). Invalid -> NaN."""
    p = np.abs(slc).astype(np.float32) ** 2
    p[~valid | ~np.isfinite(p)] = np.nan
    return p


def power_to_db(p):
    """10*log10 for positive finite power; everything else -> NaN."""
    out = np.full(p.shape, np.nan, dtype=np.float32)
    ok = np.isfinite(p) & (p > 0)
    out[ok] = 10 * np.log10(p[ok])
    return out


def multilook(power, n, transform=None):
    """Average linear power over n x n blocks (NaN-aware). Averaging in linear units,
    not dB, preserves mean power. Returns (array, transform) with pixel size scaled by n."""
    r, c = (power.shape[0] // n) * n, (power.shape[1] // n) * n
    blocks = power[:r, :c].reshape(r // n, n, c // n, n)
    with np.errstate(invalid="ignore"):
        out = np.nanmean(blocks, axis=(1, 3))
    new_t = transform * transform.scale(n, n) if transform is not None else None
    return out, new_t


# ---------------------------------------------------------------- stats and plotting

def summary_stats(values, valid=None, pcts=(1, 5, 25, 50, 75, 95, 99)):
    """Valid-pixel fraction and percentiles of a map (finite values only).
    No mean here: for dB maps the mean must be taken in linear power (see run_eda)."""
    ok = np.isfinite(values) if valid is None else valid & np.isfinite(values)
    v = values[ok]
    stats = {"n_pixels": values.size, "valid_frac": round(float(ok.mean()), 4)}
    stats.update({f"p{q}": float(np.percentile(v, q)) for q in pcts} if v.size else {})
    return stats


def extent_km(transform, shape):
    """imshow extent (left, right, bottom, top) in km of the map CRS."""
    left, top = transform.c, transform.f
    right = left + transform.a * shape[1]
    bottom = top + transform.e * shape[0]
    return [v / 1000 for v in (left, right, bottom, top)]


def plot_map(ax, arr, transform, crs, title, cbar_label, **imshow_kw):
    im = ax.imshow(arr, extent=extent_km(transform, arr.shape), interpolation="nearest", **imshow_kw)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel(f"Easting (km, {crs.to_string()})")
    ax.set_ylabel("Northing (km)")
    plt.colorbar(im, ax=ax, label=cbar_label, shrink=0.8)
    return im
