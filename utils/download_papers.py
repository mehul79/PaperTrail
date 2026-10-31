"""Download all past papers for the given subject codes into data/<code>/.

Usage: python scripts/download_papers.py
"""
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

SUBJECTS = ["UCS310", "UCS802", "UCS745", "UCS701", "UCS619", "UCS520", "UCS510", "UTA018"]  # add subject codes here

BASE = "http://172.31.19.78/qpapers/"
DELAY = 2  # seconds between requests, keep the campus server happy (PRD FR-7)
OUT = Path(__file__).resolve().parent.parent / "data"

ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
LINK = re.compile(r'href="(download\.php\?id=[^"]+)"')


def fetch(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "PaperTrail/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def list_papers(code):
    body = urllib.parse.urlencode({"ccode": code}).encode()
    html = fetch(BASE + "view1.php", body).decode("utf-8", "replace")
    papers = []
    for row in ROW.findall(html):
        link = LINK.search(row)
        if not link:
            continue
        cells = [re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in CELL.findall(row)]
        # cells: code, name, year, semester, exam type, download
        papers.append({"code": cells[0], "name": cells[1], "year": cells[2],
                       "sem": cells[3], "type": cells[4], "url": BASE + link.group(1)})
    return papers


def main():
    for code in SUBJECTS:
        done = OUT / code / ".done"
        if done.exists():
            print(f"\n{code}: already downloaded, skipping (delete {done} to redo)")
            continue
        papers = list_papers(code)
        print(f"\n{code}: found {len(papers)} PDFs")
        for p in papers:
            print(f"  {p['year']} {p['sem']} {p['type']:<4} {p['name']}")
        if not papers:
            continue

        folder = OUT / code
        folder.mkdir(parents=True, exist_ok=True)
        seen = {}
        failed = 0
        for p in papers:
            stem = f"{p['code']}_{p['year']}_{p['sem']}_{p['type']}"
            seen[stem] = seen.get(stem, 0) + 1
            if seen[stem] > 1:  # same year/sem/type listed twice
                stem += f"_{seen[stem]}"
            path = folder / f"{stem}.pdf"
            if path.exists():
                print(f"skip {path.name} (exists)")
                continue
            time.sleep(DELAY)
            try:
                path.write_bytes(fetch(p["url"]))
                print(f"saved {path.name}")
            except Exception as e:
                failed += 1
                print(f"FAILED {path.name}: {e}")
        if not failed:  # only mark complete when every PDF is on disk
            done.touch()


if __name__ == "__main__":
    main()
