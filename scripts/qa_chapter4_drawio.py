from pathlib import Path
import re
import xml.etree.ElementTree as ET


OUTPUT_DIR = Path(
    r"D:\ICS\YEAR 4\sem1\IS\model related\output\chapter4_drawio_editable"
)


def visible_values(root: ET.Element) -> str:
    return " ".join(cell.attrib.get("value", "") for cell in root.iter("mxCell"))


def main() -> None:
    documents = sorted(OUTPUT_DIR.glob("*.drawio"))
    assert len(documents) == 7, f"Expected 7 Draw.io files, found {len(documents)}"

    combined = OUTPUT_DIR / "Spendly_Chapter4_All_Diagrams.drawio"
    combined_root = ET.parse(combined).getroot()
    assert len(combined_root.findall("diagram")) == 6

    individual = [path for path in documents if path != combined]
    for path in individual:
        root = ET.parse(path).getroot()
        assert root.tag == "mxfile"
        diagrams = root.findall("diagram")
        assert len(diagrams) == 1
        model = diagrams[0].find("mxGraphModel")
        assert model is not None
        cells = model.findall("./root/mxCell")
        assert len(cells) >= 40, f"Unexpectedly few editable objects in {path.name}"
        assert any(cell.attrib.get("vertex") == "1" for cell in cells)
        assert any(cell.attrib.get("edge") == "1" for cell in cells)

    text = visible_values(combined_root)
    assert "LSTM" in text
    assert "Isolation Forest" in text
    assert "rule-based recommendation" in text
    assert "POST /api/v1/analysis/run" in text
    assert not re.search(r"linear\s+regression|multiple\s+linear", text, re.I)
    assert not re.search(r"\bv1\b", text.replace("/api/v1/", "/api/version/"), re.I)

    architecture = ET.parse(OUTPUT_DIR / "06_System_Architecture_Final.drawio").getroot()
    image_cells = [
        cell
        for cell in architecture.iter("mxCell")
        if "shape=image" in cell.attrib.get("style", "")
    ]
    assert len(image_cells) == 5, f"Expected 5 architecture images, found {len(image_cells)}"

    total_cells = sum(1 for cell in combined_root.iter("mxCell"))
    total_edges = sum(
        1 for cell in combined_root.iter("mxCell") if cell.attrib.get("edge") == "1"
    )
    print(
        f"PASS: 7 Draw.io files parsed; combined document has 6 pages, "
        f"{total_cells} cells and {total_edges} editable connectors"
    )


if __name__ == "__main__":
    main()
