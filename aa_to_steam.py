"""Convert an Apple Arcade FANTASIAN save into a Steam FANTASIAN Neo Dimension root.json.

Both versions store the same save payload; only the container differs:

    Apple Arcade   SaveDataEntity.sqlite -> ZGAMEDATAENTITY.ZDATA (zlib compressed)
                   -> {"records": [{"path": "Data/GameData0.json",
                                    "dataString": "<plaintext json>"}, ...]}

    Steam (ND)     Documents/My Games/FANTASIAN Neo Dimension/Steam/<id>/_data/root.json
                   -> {"dataString": "{\"records\": [{\"path\": ...,
                                       \"encryptedString\": \"<aes-cbc + base64>\"}]}"}

So converting is: pull the records out of the sqlite blob, AES-encrypt each
dataString with the same key fantasia.py uses, and rewrap.
"""

import argparse
import base64
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
import zlib

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

AesIV = b"Nq4G3pTQFLTCeiB7"
AesKey = b"yrhWj8EiU83kXupm"

STEAM_SAVE_DIR = os.path.join(
    os.path.expanduser("~"), "Documents", "My Games",
    "FANTASIAN Neo Dimension", "Steam")


def decrypt(data):
    return unpad(AES.new(AesKey, AES.MODE_CBC, AesIV).decrypt(data), AES.block_size)


def encrypt(data):
    return AES.new(AesKey, AES.MODE_CBC, AesIV).encrypt(pad(data, AES.block_size))


# --------------------------------------------------------------------------
# reading the Apple Arcade side
# --------------------------------------------------------------------------

def _records_from_blob(raw):
    """raw is the zlib-compressed (or plain) {"records": [...]} payload."""
    if raw[:1] == b"\x78":
        raw = zlib.decompress(raw)
    obj = json.loads(raw.decode("utf-8"))
    if "records" not in obj and "dataString" in obj:
        obj = json.loads(obj["dataString"])  # already a Steam-shaped root
    return obj["records"]


def _records_from_sqlite(db_path):
    con = sqlite3.connect(db_path)
    try:
        rows = list(con.execute(
            "SELECT ZID, ZDATA FROM ZGAMEDATAENTITY ORDER BY ZTIME DESC"))
    finally:
        con.close()
    for zid, zdata in rows:
        if zid and "root" in zid.lower() and zdata:
            return _records_from_blob(zdata)
    raise SystemExit("no root.json row found in ZGAMEDATAENTITY")


def _records_from_zip(zip_path):
    """Extract the sqlite plus its -wal/-shm so the WAL is replayed on open."""
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist()
                 if os.path.basename(n).startswith("SaveDataEntity.sqlite")
                 and not os.path.basename(n).startswith("._")]
        if not names:
            raise SystemExit(f"no SaveDataEntity.sqlite inside {zip_path}")
        tmp = tempfile.mkdtemp(prefix="fantasian_aa_")
        try:
            for n in names:
                with open(os.path.join(tmp, os.path.basename(n)), "wb") as f:
                    f.write(z.read(n))
            return _records_from_sqlite(os.path.join(tmp, "SaveDataEntity.sqlite"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def load_source_records(path):
    """Accepts the iCloud .zip, a bare .sqlite, a ZGAMEDATAENTITY json dump,
    a decompressed Apple Arcade root.json, or an existing Steam root.json."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".zip":
        return _records_from_zip(path)
    if ext in (".sqlite", ".db", ".sqlite3"):
        return _records_from_sqlite(path)

    with open(path, "rb") as f:
        blob = f.read()

    if blob.lstrip()[:1] == b"[":
        # a table dump: [{"ZID": "root.json", "ZDATA": "<base64>", ...}, ...]
        for row in json.loads(blob.decode("utf-8")):
            if "ZDATA" in row and "root" in str(row.get("ZID", "root")).lower():
                return _records_from_blob(base64.b64decode(row["ZDATA"]))
        raise SystemExit(f"no row with a ZDATA blob in {path}")
    return _records_from_blob(blob)


# --------------------------------------------------------------------------
# record helpers
# --------------------------------------------------------------------------

def record_plaintext(record):
    if "dataString" in record:
        return record["dataString"]
    return decrypt(base64.b64decode(record["encryptedString"])).decode("utf-8")


def describe(record):
    try:
        data = json.loads(record_plaintext(record))
        d = dict(zip(data["keys"], data["values"]))
        gsi = json.loads(d.get("GameSystemInfo", "{}"))
        hours = gsi.get("_playTimeSec", 0) / 3600.0
        return (f"{record.get('path', '?'):<24} {d.get('Date', '?'):<20} "
                f"{hours:5.1f}h {gsi.get('_money', 0):>8} G  map={gsi.get('_mapId', '?')}")
    except Exception as exc:  # diagnostics only
        return f"{record.get('path', '?'):<24} <unreadable: {exc}>"


def to_steam_record(record):
    return {
        "path": record["path"],
        "encryptedString": base64.b64encode(
            encrypt(record_plaintext(record).encode("utf-8"))).decode("utf-8"),
    }


def find_steam_root():
    if not os.path.isdir(STEAM_SAVE_DIR):
        return None
    for user in sorted(os.listdir(STEAM_SAVE_DIR)):
        candidate = os.path.join(STEAM_SAVE_DIR, user, "_data", "root.json")
        if os.path.isfile(candidate):
            return candidate
    return None


def slot_number(path):
    base = os.path.basename(path)
    return base[len("GameData"):-len(".json")] if base.startswith("GameData") else base


def canonical_order(records):
    """Order records the way the game writes them: manual slot 1, the autosave
    (GameData10), then manual slots 2..n.  fantasia.py relies on this -- it
    treats records[1] as the quicksave and records[0]/records[2:] as slots."""
    def key(record):
        n = slot_number(record["path"])
        if not n.isdigit():
            return (3, n)
        n = int(n)
        if n == 0:
            return (0, 0)
        if n == 10:
            return (1, 0)
        return (2, n)
    return sorted(records, key=key)


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Convert an Apple Arcade FANTASIAN save to Steam Neo Dimension format.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, width=100))
    ap.add_argument(
        "source",
        help="iCloud FANTASIAN.zip, SaveDataEntity.sqlite, ZGAMEDATAENTITY json dump, "
             "or an already-decompressed Apple Arcade root.json")
    ap.add_argument(
        "-o", "--output", default="root.json",
        help="where to write the Steam-format root.json (default: root.json)")
    ap.add_argument(
        "-t", "--template", metavar="STEAM_ROOT_JSON",
        help="an existing Steam root.json to merge into.  Strongly recommended: slots "
             "present in the template but not in the source are kept, and the layout "
             "the game itself wrote is preserved.")
    ap.add_argument(
        "--auto-template", action="store_true",
        help=f"look for the template under {STEAM_SAVE_DIR}")
    ap.add_argument(
        "--slots", metavar="PATH_OR_N", nargs="*", default=None,
        help="only import these slots, by GameData number (e.g. --slots 0 10) or by full "
             "path.  Default: all of them.")
    ap.add_argument(
        "--list", action="store_true", help="list the source slots and exit")
    args = ap.parse_args()

    src_records = load_source_records(args.source)
    print(f"Found {len(src_records)} slot(s) in {args.source}:")
    for r in src_records:
        print("  " + describe(r))
    if args.list:
        return

    if args.slots:
        wanted = set(args.slots)
        kept = [r for r in src_records
                if r["path"] in wanted or slot_number(r["path"]) in wanted]
        if not kept:
            raise SystemExit(f"--slots {args.slots} matched nothing")
        src_records = kept

    template_path = args.template
    if args.auto_template and not template_path:
        template_path = find_steam_root()
        if template_path:
            print(f"Using template {template_path}")
        else:
            print(f"No Steam root.json found under {STEAM_SAVE_DIR}", file=sys.stderr)

    if template_path:
        with open(template_path, encoding="utf-8") as f:
            root = json.load(f)
        records = json.loads(root["dataString"])["records"]
        print(f"Template has {len(records)} slot(s):")
        for r in records:
            print("  " + describe(r))
    else:
        print("No template given -- writing a root.json from scratch.  If the game "
              "rejects it, make one save in the Steam version first and rerun with "
              "--auto-template.")
        root, records = {}, []
        src_records = canonical_order(src_records)

    print("Importing:")
    by_path = {r["path"]: i for i, r in enumerate(records)}
    for src in src_records:
        new = to_steam_record(src)
        if new["path"] in by_path:
            records[by_path[new["path"]]] = new
            print(f"  replaced {new['path']}")
        else:
            records.append(new)
            print(f"  added    {new['path']}")

    root["dataString"] = json.dumps({"records": records}, separators=(",", ":"))

    # round-trip check: everything we wrote must decrypt back to valid json
    for r in json.loads(root["dataString"])["records"]:
        json.loads(record_plaintext(r))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(root, f, indent=4)
    print(f"\nWrote {args.output} ({len(records)} slots).  Back up your Steam save, "
          f"then copy this over <Steam save dir>/_data/root.json")


if __name__ == "__main__":
    main()
