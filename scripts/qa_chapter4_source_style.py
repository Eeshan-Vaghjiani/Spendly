from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image


OUTPUT_DIR = Path(
    r"D:\ICS\YEAR 4\sem1\IS\model related\output\chapter4_source_style_final"
)


def main() -> None:
    svgs = sorted(OUTPUT_DIR.glob("*.svg"))
    pngs = sorted(OUTPUT_DIR.glob("*.png"))

    assert len(svgs) == 6, f"Expected 6 SVGs, found {len(svgs)}"
    assert len(pngs) == 7, f"Expected 7 PNGs, found {len(pngs)}"

    for svg in svgs:
        ET.parse(svg)

    sizes: dict[str, tuple[int, int]] = {}
    for png in pngs:
        with Image.open(png) as image:
            image.verify()
        with Image.open(png) as image:
            sizes[png.name] = image.size

    assert all(width >= 1800 and height >= 1800 for width, height in sizes.values())

    source = "\n".join(svg.read_text(encoding="utf-8") for svg in svgs)
    visible = " ".join(
        " ".join(ET.parse(svg).getroot().itertext()) for svg in svgs
    )
    visible = re.sub(r"\s+", " ", visible)
    assert not re.search(r"linear\s+regression|multiple\s+linear", visible, re.I)

    required = [
        "LSTM",
        "Isolation Forest",
        "rule-based recommendation",
        "POST /api/v1/analysis/run",
        "review_status",
        "reviewed_at",
        "password_hash OR google_subject",
        "Register Account",
        "Sign In",
        "Issue detected?",
    ]
    missing = [term for term in required if term.casefold() not in visible.casefold()]
    assert not missing, f"Required content missing: {missing}"
    without_api_version = visible.replace("/api/v1/", "/api/version/")
    assert not re.search(r"\bv1\b", without_api_version, re.I), (
        "The model suffix 'v1' remains"
    )

    font_sizes = []
    for svg in svgs:
        for element in ET.parse(svg).getroot().iter():
            if (
                element.tag.endswith("text")
                and "".join(element.itertext()).strip()
                and element.attrib.get("font-size")
            ):
                font_sizes.append(float(element.attrib["font-size"]))
    assert font_sizes and min(font_sizes) >= 14, min(font_sizes)

    architecture = (OUTPUT_DIR / "06_System_Architecture_Final.svg").read_text(
        encoding="utf-8"
    )
    assert architecture.count("<image") >= 4, "Architecture logos were not preserved"

    print(
        f"PASS: {len(svgs)} SVGs parsed; {len(pngs)} PNGs verified; "
        f"minimum visible font {min(font_sizes):g} px"
    )
    for name, (width, height) in sizes.items():
        print(f"{name}: {width}x{height}")


if __name__ == "__main__":
    main()
