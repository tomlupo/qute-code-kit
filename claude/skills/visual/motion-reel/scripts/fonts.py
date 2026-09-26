# /// script
# requires-python = ">=3.10"
# ///
"""Download Google Fonts into a project, so headless Chrome renders them offline.

    uv run fonts.py PROJECT --family "Inter:wght@100..900" --family "DM Mono:wght@400;500"

Writes PROJECT/fonts/*.woff2 and PROJECT/fonts.css. The latin and latin-ext
subsets are kept by default, so Polish and most European diacritics render; pass
--subsets to change that. Family specs use the Google Fonts css2 syntax.
"""

import argparse
import re
import urllib.request
from pathlib import Path
from urllib.parse import quote

from project_files import output_dir, write_file

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
DEFAULT_FAMILIES = ["Inter:wght@100..900", "DM Mono:wght@400;500"]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("project", type=Path)
    ap.add_argument(
        "--family",
        action="append",
        help="css2 family spec; repeatable (default: Inter + DM Mono)",
    )
    ap.add_argument("--subsets", default="latin,latin-ext")
    a = ap.parse_args()
    families = a.family or DEFAULT_FAMILIES
    keep = set(a.subsets.split(","))
    query = "&".join(
        "family=" + quote(f, safe=":@.;,").replace("%20", "+") for f in families
    )
    out_dir = output_dir(a.project / "fonts", a.project)  # before any download
    css = fetch(f"https://fonts.googleapis.com/css2?{query}&display=block").decode()
    faces = []
    for subset, body in re.findall(r"/\*\s*(\S+)\s*\*/\s*@font-face\s*{([^}]*)}", css):
        if subset not in keep:
            continue
        fam = re.search(r"font-family: '([^']+)'", body).group(1)
        style = re.search(r"font-style: (\w+)", body).group(1)
        weight = re.search(r"font-weight: ([\d ]+);", body).group(1)
        url = re.search(r"url\((\S+?)\)", body).group(1)
        rng = re.search(r"unicode-range: ([^;]+);", body)
        name = (
            f"{fam.replace(' ', '')}-{style}-{weight.replace(' ', '_')}-{subset}.woff2"
        )
        write_file(out_dir / name, fetch(url), a.project)
        faces.append(
            f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
            f"src:url(fonts/{name}) format('woff2');"
            + (f"unicode-range:{rng.group(1)};" if rng else "")
            + "font-display:block}"
        )
        print("  ", name)
    if not faces:
        raise SystemExit(
            f"no faces matched subsets {sorted(keep)} — check the family specs"
        )
    write_file(a.project / "fonts.css", "\n".join(faces) + "\n", a.project)
    print(f"wrote {a.project / 'fonts.css'}: {len(faces)} faces")


if __name__ == "__main__":
    main()
