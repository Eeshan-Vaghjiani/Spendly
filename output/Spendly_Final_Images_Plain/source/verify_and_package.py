"""Verify the final image pack and produce a thumbnail index and distributable ZIP."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

PACK = Path(__file__).resolve().parent.parent
ROOT = PACK.parent.parent
NS = {"s": "http://www.w3.org/2000/svg"}
EXPECTED = [
    "01_Database_Schema", "02_Entity_Relationship_Diagram", "03_Use_Case_Diagram",
    "04_Activity_Diagram", "05_Sequence_Diagram", "06_Class_Diagram",
    "07_System_Architecture", "08_Wireframe_Dashboard", "09_Wireframe_Add_Transaction",
    "10_Wireframe_Forecast_Results", "11_Wireframe_Admin_Dashboard",
    "12_Wireframe_Budgets", "13_Wireframe_Spending_Check",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    schema = json.loads((PACK / "source/schema.json").read_text(encoding="utf-8"))
    assert sha(ROOT / schema["source"]) == schema["source_sha256"], "Schema source changed"
    assert len(schema["tables"]) == 11
    assert sum(len(t["columns"]) for t in schema["tables"]) == 97
    fks = [(t["name"], c["name"], f["target"], f["ondelete"])
           for t in schema["tables"] for c in t["columns"] for f in c["foreign_keys"]]
    assert len(fks) == 10
    assert set(fks) == {
        ("transactions", "user_id", "users.id", "CASCADE"),
        ("budgets", "user_id", "users.id", "CASCADE"),
        ("analysis_runs", "user_id", "users.id", "CASCADE"),
        ("forecasts", "user_id", "users.id", "CASCADE"),
        ("forecasts", "analysis_run_id", "analysis_runs.id", "CASCADE"),
        ("anomaly_alerts", "user_id", "users.id", "CASCADE"),
        ("anomaly_alerts", "analysis_run_id", "analysis_runs.id", "CASCADE"),
        ("anomaly_alerts", "transaction_id", "transactions.id", "SET NULL"),
        ("recommendations", "user_id", "users.id", "CASCADE"),
        ("recommendations", "analysis_run_id", "analysis_runs.id", "CASCADE"),
    }
    routing = json.loads((PACK / "source/schema_routes.json").read_text())
    assert len(routing["routes"]) == len(fks)
    assert {(r["child"], r["parent"]) for r in routing["routes"]} == {(t+"."+c, target) for t,c,target,_ in fks}
    for extension in ("png", "svg"):
        assert sorted(p.stem for p in (PACK / extension).glob("*." + extension)) == EXPECTED
    manifest = json.loads((PACK / "source/manifest.json").read_text(encoding="utf-8"))
    assert sorted(item["name"] for item in manifest) == EXPECTED
    rendered = []
    for name in EXPECTED:
        svg_path = PACK / "svg" / (name + ".svg")
        png_path = PACK / "png" / (name + ".png")
        svg = ET.parse(svg_path).getroot()
        texts = ["".join(e.itertext()) for e in svg.findall(".//s:text", NS)]
        assert not re.search(r"symptom|disease|malaria|\bNLP\b", " ".join(texts), re.I)
        assert not svg.findall(".//s:script", NS)
        for element in svg.findall(".//s:image", NS):
            assert element.get("{http://www.w3.org/1999/xlink}href", "").startswith("data:image/")
        im = Image.open(png_path).convert("RGB")
        r, g, b = im.split()
        monochrome = not ImageChops.difference(r, g).getbbox() and not ImageChops.difference(r, b).getbbox()
        assert bool(monochrome) == (name != "07_System_Architecture"), name + " colour check failed"
        expected_width = 1800 if name.startswith(("08_", "09_", "10_", "12_", "13_")) else 4000
        assert im.width == expected_width
        assert ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox(), "Blank image"
        rendered.append({"name": name, "width": im.width, "height": im.height,
                         "monochrome": bool(monochrome), "svg_sha256": sha(svg_path), "png_sha256": sha(png_path)})

    # Inspect real SVG text within each table/column group, not just the source metadata.
    full = ET.parse(PACK / "svg/01_Database_Schema.svg").getroot()
    erd = ET.parse(PACK / "svg/02_Entity_Relationship_Diagram.svg").getroot()
    for table in schema["tables"]:
        group = full.find(f".//s:g[@id='table-{table['name']}']", NS)
        assert group is not None
        assert erd.find(f".//s:g[@id='table-{table['name']}']", NS) is not None
        column_groups = group.findall("s:g", NS)
        assert len(column_groups) == len(table["columns"])
        for column, cg in zip(table["columns"], column_groups):
            assert cg.get("data-column") == column["name"]
            drawn = ["".join(e.itertext()) for e in cg.findall("s:text", NS)]
            flags = [flag for flag, yes in (("PK", column["pk"]), ("FK", bool(column["foreign_keys"])), ("UQ", column["unique"])) if yes]
            sql_type = column["type"].replace("TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP").replace("INTEGER", "INT").replace(" ", "")
            assert drawn == ["/".join(flags), column["name"] + (" ?" if column["nullable"] else ""), sql_type]
    for item in json.loads((PACK / "assets/sources.json").read_text()):
        assert sha(PACK / "assets" / item["file"]) == item["sha256"]

    # Documentation-only task must not introduce tracked application changes.
    tracked = subprocess.check_output(["git", "diff", "--name-only", "HEAD", "--", "backend", "mobile", "docs"], cwd=ROOT, text=True)
    assert not tracked.strip(), "Review tracked application changes before packaging"
    report = {"verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_sha256": schema["source_sha256"], "tables": 11, "columns": 97, "foreign_keys": 10,
              "all_svg_files_parse": True, "image_count": len(EXPECTED), "schema_text_matches_metadata": True,
              "all_non_architecture_images_monochrome": True, "official_asset_hashes_unchanged": True,
              "tracked_application_changes": False,
              "visual_review": "Revised architecture, schema, sequence diagram and two new wireframes inspected separately. Previously approved images retained. Automated checks do not replace visual review.",
              "figures": rendered}
    (PACK / "source/verification_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    cell_w, cell_h, gap, margin = 790, 645, 32, 42
    rows = (len(EXPECTED)+3)//4
    sheet = Image.new("RGB", (margin * 2 + cell_w * 4 + gap * 3, 150 + cell_h * rows + gap * (rows-1) + margin), "white")
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 38)
    label_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 25)
    draw.text((margin, 36), "SPENDLY - FINAL PLAIN IMAGE SET", fill="black", font=title_font)
    draw.text((margin, 90), "Thumbnail index only. Use the individual high-resolution PNG files.", fill="black", font=label_font)
    for index, name in enumerate(EXPECTED):
        x = margin + (index % 4) * (cell_w + gap)
        y = 150 + (index // 4) * (cell_h + gap)
        draw.rectangle((x, y, x + cell_w, y + cell_h), outline="#b5b5b5", width=1)
        label = name.replace("_", " ")
        draw.text((x + 18, y + 15), label, font=label_font, fill="black")
        thumb = Image.open(PACK / "png" / (name + ".png")).convert("RGB")
        thumb.thumbnail((cell_w - 36, cell_h - 90), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 68 + (cell_h - 90 - thumb.height) // 2))
    sheet.save(PACK / "Preview_All_Images.png")

    archive = PACK.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for file in sorted(PACK.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts:
                z.write(file, Path(PACK.name) / file.relative_to(PACK))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert sum(name.endswith(".png") and "/png/" in name for name in z.namelist()) == len(EXPECTED)
    print(json.dumps({"checks": "passed", "images": len(EXPECTED), "tables": 11, "columns": 97,
                      "foreign_keys": 10, "zip": str(archive), "zip_bytes": archive.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
