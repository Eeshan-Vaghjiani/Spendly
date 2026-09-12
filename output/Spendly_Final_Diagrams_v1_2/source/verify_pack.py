"""Structural/content verification for the final diagram pack (visual QA is separate)."""
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image
from pypdf import PdfReader

PACK = Path(__file__).resolve().parent.parent
ROOT = PACK.parent.parent
NS = {"s": "http://www.w3.org/2000/svg"}


def main():
    schema = json.loads((PACK / "source/schema.json").read_text(encoding="utf-8"))
    manifest = json.loads((PACK / "source/figure_manifest.json").read_text(encoding="utf-8"))
    reader = PdfReader(PACK / "Spendly_Final_Diagrams.pdf")
    assert len(reader.pages) == len(manifest) == 7
    assert len(list((PACK / "svg").glob("*.svg"))) == 7
    assert len(list((PACK / "png").glob("*.png"))) == 7
    assert hashlib.sha256((ROOT / schema["source"]).read_bytes()).hexdigest() == schema["source_sha256"]
    counts = {"tables": len(schema["tables"]), "columns": sum(len(t["columns"]) for t in schema["tables"]),
              "foreign_keys": sum(len(c["foreign_keys"]) for t in schema["tables"] for c in t["columns"])}
    assert counts == {"tables": 11, "columns": 97, "foreign_keys": 10}
    report = {"schema_counts": counts, "pages": [], "source_schema_unchanged": True}
    for i, item in enumerate(manifest):
        svg = ET.parse(PACK / "svg" / (item["name"] + ".svg"))
        text = [t.text or "" for t in svg.findall(".//s:text", NS)]
        assert len(text) == item["text_elements"]
        pdf_text = reader.pages[i].extract_text()
        assert "SPENDLY" in pdf_text and "FIGURE" in pdf_text
        assert "\ufffd" not in pdf_text
        if i == 0:
            for table in schema["tables"]:
                assert table["name"].upper() in text
                for column in table["columns"]:
                    expected = column["name"] + (" ?" if column["nullable"] else "")
                    assert expected in text, (table["name"], column["name"])
        with Image.open(PACK / "png" / (item["name"] + ".png")) as image:
            image.verify()
        with Image.open(PACK / "png" / (item["name"] + ".png")) as image:
            assert image.width >= 2600 and image.height >= 2300
            dimensions = [image.width, image.height]
        report["pages"].append({"figure": i + 1, "name": item["name"], "png_pixels": dimensions, "svg_text_nodes": len(text), "pdf_text_characters": len(pdf_text)})
    (PACK / "source/verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
