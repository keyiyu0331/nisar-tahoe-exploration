"""One-time NASA Earthdata Login setup: stores credentials in ~/.netrc (chmod 600).

Run this yourself in a terminal (it prompts with hidden input):

    .venv/bin/python setup_earthdata_auth.py

Credentials are never written inside the project directory.
Use --test to only check that an existing ~/.netrc entry works.
"""
import getpass
import netrc
import os
import sys
from pathlib import Path

HOST = "urs.earthdata.nasa.gov"
NETRC = Path.home() / ".netrc"
# Small GUNW file from outputs/scene_inventory_selected.csv used for a 8-byte test read
TEST_URL = ("https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GUNW_PROVISIONAL_V1/"
            "NISAR_L2_PR_GUNW_004_042_D_069_005_4000_SH_20251101T025606_20251101T025641_20251113T025606_20251113T025641_P05023_N_F_J_001/"
            "NISAR_L2_PR_GUNW_004_042_D_069_005_4000_SH_20251101T025606_20251101T025641_20251113T025606_20251113T025641_P05023_N_F_J_001.h5")


def has_entry():
    try:
        return netrc.netrc(NETRC).authenticators(HOST) is not None
    except (FileNotFoundError, netrc.NetrcParseError):
        return False


def write_entry():
    user = input("Earthdata username: ").strip()
    pw = getpass.getpass("Earthdata password (hidden): ")
    with open(NETRC, "a") as f:
        f.write(f"\nmachine {HOST}\n    login {user}\n    password {pw}\n")
    os.chmod(NETRC, 0o600)
    print(f"Wrote entry for {HOST} to {NETRC} (permissions 600).")


def test_access():
    sys.path.insert(0, str(Path(__file__).parent))
    from sar_utils import open_remote

    with open_remote(TEST_URL) as f:
        sig = f.read(8)
    ok = sig == b"\x89HDF\r\n\x1a\n"
    print("Access OK: HDF5 signature read." if ok else f"Unexpected response bytes: {sig!r}")
    return ok


if __name__ == "__main__":
    if "--test" not in sys.argv:
        if has_entry():
            print(f"{NETRC} already has an entry for {HOST}; leaving it unchanged.")
        else:
            write_entry()
    sys.exit(0 if test_access() else 1)
