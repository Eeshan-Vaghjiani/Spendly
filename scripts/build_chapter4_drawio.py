from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re
import urllib.parse
import xml.etree.ElementTree as ET


ROOT = Path(r"D:\ICS\YEAR 4\sem1\IS\model related")
SVG_DIR = ROOT / "output" / "chapter4_source_style_final"
OUT_DIR = ROOT / "output" / "chapter4_drawio_editable"

FIGURES = [
    ("01_Database_Schema_Final.svg", "Database Schema"),
    ("02_Final_Use_Case_Diagram.svg", "Final Use Case Diagram"),
    (
        "03_Activity_Add_Import_Transaction_Final.svg",
        "Activity - Add or Import Transaction",
    ),
    (
        "04_Activity_Generate_Spending_Insights_Final.svg",
        "Activity - Generate Spending Insights",
    ),
    (
        "05_Sequence_Generate_Spending_Insights_Final.svg",
        "Sequence - Generate Spending Insights",
    ),
    ("06_System_Architecture_Final.svg", "System Architecture"),
]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def number(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.search(r"-?[0-9]+(?:\.[0-9]+)?", value)
    return float(match.group()) if match else default


def tidy(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-8):
        return str(int(round(value)))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def points(value: str) -> list[tuple[float, float]]:
    pairs = []
    for token in value.strip().split():
        x, y = token.split(",", 1)
        pairs.append((float(x), float(y)))
    return pairs


def style_value(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    return "none" if value.casefold() == "none" else value


def vertex(
    graph_root: ET.Element,
    cell_id: str,
    value: str,
    style: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> ET.Element:
    cell = ET.SubElement(
        graph_root,
        "mxCell",
        {
            "id": cell_id,
            "value": value,
            "style": style,
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(
        cell,
        "mxGeometry",
        {
            "x": tidy(x),
            "y": tidy(y),
            "width": tidy(max(width, 1)),
            "height": tidy(max(height, 1)),
            "as": "geometry",
        },
    )
    return cell


def edge(
    graph_root: ET.Element,
    cell_id: str,
    style: str,
    route: list[tuple[float, float]],
) -> ET.Element:
    cell = ET.SubElement(
        graph_root,
        "mxCell",
        {
            "id": cell_id,
            "value": "",
            "style": style,
            "edge": "1",
            "parent": "1",
        },
    )
    geometry = ET.SubElement(
        cell,
        "mxGeometry",
        {"relative": "1", "as": "geometry"},
    )
    ET.SubElement(
        geometry,
        "mxPoint",
        {"x": tidy(route[0][0]), "y": tidy(route[0][1]), "as": "sourcePoint"},
    )
    ET.SubElement(
        geometry,
        "mxPoint",
        {"x": tidy(route[-1][0]), "y": tidy(route[-1][1]), "as": "targetPoint"},
    )
    if len(route) > 2:
        waypoint_array = ET.SubElement(geometry, "Array", {"as": "points"})
        for x, y in route[1:-1]:
            ET.SubElement(
                waypoint_array,
                "mxPoint",
                {"x": tidy(x), "y": tidy(y)},
            )
    return cell


def graph_model(width: int, height: int) -> tuple[ET.Element, ET.Element]:
    model = ET.Element(
        "mxGraphModel",
        {
            "dx": "1200",
            "dy": "800",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": str(width),
            "pageHeight": str(height),
            "math": "0",
            "shadow": "0",
            "background": "#ffffff",
        },
    )
    graph_root = ET.SubElement(model, "root")
    ET.SubElement(graph_root, "mxCell", {"id": "0"})
    ET.SubElement(graph_root, "mxCell", {"id": "1", "parent": "0"})
    return model, graph_root


def convert_svg(svg_path: Path) -> tuple[ET.Element, dict[str, int]]:
    svg_tree = ET.parse(svg_path)
    svg_root = svg_tree.getroot()
    width = int(number(svg_root.attrib.get("width"), 1600))
    height = int(number(svg_root.attrib.get("height"), 1200))
    model, graph_root = graph_model(width, height)

    excluded: set[ET.Element] = set()
    for element in svg_root:
        if local_name(element.tag) == "defs":
            excluded.update(element.iter())

    counts = {"shapes": 0, "text": 0, "connectors": 0, "images": 0}
    counter = 2

    for element in svg_root.iter():
        if element is svg_root or element in excluded:
            continue
        tag = local_name(element.tag)
        if tag in {"title", "desc", "metadata"}:
            continue
        cell_id = str(counter)
        counter += 1

        stroke = style_value(element.attrib.get("stroke"), "none")
        fill = style_value(element.attrib.get("fill"), "none")
        stroke_width = number(element.attrib.get("stroke-width"), 1.0)
        dashed = "dashed=1;" if element.attrib.get("stroke-dasharray") else ""

        if tag == "rect":
            x = number(element.attrib.get("x"))
            y = number(element.attrib.get("y"))
            raw_width = element.attrib.get("width", "0")
            raw_height = element.attrib.get("height", "0")
            rect_width = width if "%" in raw_width else number(raw_width)
            rect_height = height if "%" in raw_height else number(raw_height)
            rounded = 1 if number(element.attrib.get("rx")) > 0 else 0
            style = (
                f"rounded={rounded};whiteSpace=wrap;html=0;"
                f"fillColor={fill};strokeColor={stroke};strokeWidth={tidy(stroke_width)};"
                f"{dashed}"
            )
            vertex(graph_root, cell_id, "", style, x, y, rect_width, rect_height)
            counts["shapes"] += 1

        elif tag in {"ellipse", "circle"}:
            if tag == "ellipse":
                rx = number(element.attrib.get("rx"))
                ry = number(element.attrib.get("ry"))
                cx = number(element.attrib.get("cx"))
                cy = number(element.attrib.get("cy"))
            else:
                rx = ry = number(element.attrib.get("r"))
                cx = number(element.attrib.get("cx"))
                cy = number(element.attrib.get("cy"))
            style = (
                f"ellipse;whiteSpace=wrap;html=0;fillColor={fill};"
                f"strokeColor={stroke};strokeWidth={tidy(stroke_width)};{dashed}"
            )
            vertex(graph_root, cell_id, "", style, cx - rx, cy - ry, rx * 2, ry * 2)
            counts["shapes"] += 1

        elif tag == "polygon":
            route = points(element.attrib.get("points", ""))
            if len(route) < 3:
                continue
            xs = [point[0] for point in route]
            ys = [point[1] for point in route]
            left, top = min(xs), min(ys)
            polygon_width, polygon_height = max(xs) - left, max(ys) - top
            if len(route) == 4:
                shape = "rhombus"
            else:
                apex = route[1]
                distances = {
                    "east": apex[0] - left,
                    "west": max(xs) - apex[0],
                    "south": apex[1] - top,
                    "north": max(ys) - apex[1],
                }
                direction = max(distances, key=distances.get)
                shape = f"triangle;direction={direction}"
            style = (
                f"{shape};whiteSpace=wrap;html=0;fillColor={fill};"
                f"strokeColor={stroke};strokeWidth={tidy(stroke_width)};"
            )
            vertex(
                graph_root,
                cell_id,
                "",
                style,
                left,
                top,
                polygon_width,
                polygon_height,
            )
            counts["shapes"] += 1

        elif tag == "polyline":
            route = points(element.attrib.get("points", ""))
            if len(route) < 2:
                continue
            has_arrow = bool(element.attrib.get("marker-end"))
            style = (
                "edgeStyle=none;orthogonalLoop=1;jettySize=auto;html=0;rounded=0;"
                f"strokeColor={stroke};strokeWidth={tidy(stroke_width)};"
                f"endArrow={'block' if has_arrow else 'none'};"
                f"endFill={'1' if has_arrow else '0'};endSize=8;{dashed}"
            )
            edge(graph_root, cell_id, style, route)
            counts["connectors"] += 1

        elif tag == "text":
            label = "".join(element.itertext()).strip()
            if not label:
                continue
            font_size = number(element.attrib.get("font-size"), 18)
            font_weight = number(element.attrib.get("font-weight"), 400)
            anchor = element.attrib.get("text-anchor", "start")
            x = number(element.attrib.get("x"))
            baseline_y = number(element.attrib.get("y"))
            text_width = min(max(len(label) * font_size * 0.59 + 22, 46), width * 0.9)
            text_height = font_size * 1.5
            if anchor == "middle":
                left = x - text_width / 2
                align = "center"
            elif anchor == "end":
                left = x - text_width
                align = "right"
            else:
                left = x
                align = "left"
            top = baseline_y - font_size * 1.08
            font_style = 1 if font_weight >= 600 else 0
            font_color = style_value(element.attrib.get("fill"), "#111111")
            style = (
                "text;html=0;strokeColor=none;fillColor=none;whiteSpace=wrap;"
                f"overflow=visible;align={align};verticalAlign=middle;"
                f"fontFamily=Arial;fontSize={tidy(font_size)};fontStyle={font_style};"
                f"fontColor={font_color};spacing=0;"
            )
            vertex(
                graph_root,
                cell_id,
                label,
                style,
                left,
                top,
                text_width,
                text_height,
            )
            counts["text"] += 1

        elif tag == "image":
            href = ""
            for key, value in element.attrib.items():
                if key == "href" or key.endswith("}href"):
                    href = value
                    break
            if not href:
                continue
            safe_href = urllib.parse.quote(href, safe=":/,+=")
            style = (
                "shape=image;verticalLabelPosition=bottom;verticalAlign=top;"
                f"imageAspect=1;aspect=fixed;image={safe_href};"
            )
            vertex(
                graph_root,
                cell_id,
                "",
                style,
                number(element.attrib.get("x")),
                number(element.attrib.get("y")),
                number(element.attrib.get("width")),
                number(element.attrib.get("height")),
            )
            counts["images"] += 1

    return model, counts


def mxfile() -> ET.Element:
    return ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "agent": "Codex",
            "version": "24.7.17",
            "type": "device",
            "compressed": "false",
        },
    )


def add_diagram(container: ET.Element, name: str, model: ET.Element) -> None:
    diagram_id = hashlib.sha1(name.encode("utf-8")).hexdigest()[:12]
    diagram = ET.SubElement(container, "diagram", {"id": diagram_id, "name": name})
    diagram.append(model)


def write_xml(path: Path, root: ET.Element) -> None:
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    combined = mxfile()
    report = []

    for svg_name, page_name in FIGURES:
        model, counts = convert_svg(SVG_DIR / svg_name)
        individual = mxfile()
        add_diagram(individual, page_name, model)
        output_name = Path(svg_name).with_suffix(".drawio").name
        write_xml(OUT_DIR / output_name, individual)

        combined_model, _ = convert_svg(SVG_DIR / svg_name)
        add_diagram(combined, page_name, combined_model)
        report.append((output_name, counts))

    write_xml(OUT_DIR / "Spendly_Chapter4_All_Diagrams.drawio", combined)

    readme_lines = [
        "# Spendly Chapter 4 - Editable Draw.io Files",
        "",
        "Open `Spendly_Chapter4_All_Diagrams.drawio` in diagrams.net / Draw.io to edit all six figures as separate pages.",
        "The six individual `.drawio` files are provided when one diagram per file is preferred.",
        "",
        "All visible labels, boxes, UML symbols, connectors, arrowheads and architecture logos were converted into Draw.io objects.",
        "The model names are LSTM, Isolation Forest and rule-based recommendation engine, with no model-version suffix.",
        "The `/api/v1/analysis/run` text is an API route version and is intentionally retained.",
        "",
        "Generated files:",
    ]
    readme_lines.extend(f"- `{name}`" for name, _ in report)
    readme_lines.extend(
        [
            "- `Spendly_Chapter4_All_Diagrams.drawio`",
            "",
            "Object conversion summary:",
        ]
    )
    for name, counts in report:
        readme_lines.append(
            f"- `{name}`: {counts['shapes']} shapes, {counts['text']} labels, "
            f"{counts['connectors']} connectors, {counts['images']} logos/images"
        )
    (OUT_DIR / "README_EDITABLE.md").write_text(
        "\n".join(readme_lines) + "\n", encoding="utf-8"
    )

    print(f"Built 7 Draw.io documents in {OUT_DIR}")
    for name, counts in report:
        print(f"{name}: {counts}")


if __name__ == "__main__":
    main()
