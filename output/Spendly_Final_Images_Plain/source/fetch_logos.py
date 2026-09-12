"""Fetch unmodified logos from official project sites for architecture only."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

PACK = Path(__file__).resolve().parent.parent
ASSETS = PACK / "assets"
LOGOS = {
    "flutter.svg": "https://flutter.dev/assets/flutter-logo.6ed04a8cd70b7aa540c6ec302a4e936c.svg",
    "python.svg": "https://s3.dualstack.us-east-2.amazonaws.com/pythondotorg-assets/media/files/python-logo-only.svg",
    "flask.svg": "https://flask.palletsprojects.com/en/stable/_images/flask-name.svg",
    "scikit-learn.svg": "https://scikit-learn.org/stable/_static/scikit-learn-logo-without-subtitle.svg",
    "postgresql.png": "https://www.postgresql.org/media/img/about/press/elephant.png",
}


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    manifest = []
    for filename, url in LOGOS.items():
        data = urlopen(Request(url, headers={"User-Agent": "Spendly-documentation/1.0"}), timeout=30).read()
        if filename.endswith(".svg"):
            assert b"<svg" in data[:5000]
            assert b"<script" not in data.lower()
        else:
            assert data.startswith(b"\x89PNG")
        (ASSETS / filename).write_bytes(data)
        manifest.append({"file": filename, "url": url, "sha256": hashlib.sha256(data).hexdigest()})
        print(filename, len(data))
    (ASSETS / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
