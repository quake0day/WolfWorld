"""Check repository-local Markdown links, images, and heading fragments."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
docs = [ROOT / name for name in ("README.md", "CONTRIBUTING.md", "SECURITY.md")]
docs += list((ROOT / "docs").rglob("*.md")) + [ROOT / "worker/README.md"]
errors = []


def heading_ids(text):
    ids, counts = set(), {}
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    for title in re.findall(r"^#{1,6}\s+(.+)$", text, re.M):
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        ids.add(f"{slug}-{count}" if count else slug)
    return ids


for doc in docs:
    content = doc.read_text(encoding="utf-8")
    urls = re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", content)
    urls += re.findall(r'<img[^>]+src="([^"]+)"', content)
    for url in urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        target = (doc.parent / unquote(parts.path)).resolve() if parts.path else doc
        if not target.exists():
            errors.append(f"{doc.relative_to(ROOT)}: missing {url}")
        elif parts.fragment and target.suffix == ".md":
            if unquote(parts.fragment) not in heading_ids(target.read_text(encoding="utf-8")):
                errors.append(f"{doc.relative_to(ROOT)}: missing anchor {url}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"Local links and heading anchors checked in {len(docs)} documents")
