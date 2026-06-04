"""連結圖匯出：Gephi GEXF / GraphML。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

from sitespider.link_graph import build_link_graph_data
from sitespider.report_theme import report_styles_bundle, report_topbar


def export_link_graph_gexf(
    report: CrawlReport,
    path: Path,
    *,
    max_nodes: int = 800,
) -> None:
    data = build_link_graph_data(report, max_nodes=max_nodes, edge_cap=5000, node_cap=max_nodes)
    nodes = data["nodes"]
    edges = data["edges"]
    id_map = {n["id"]: str(i) for i, n in enumerate(nodes)}

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">',
        '<graph mode="static" defaultedgetype="directed">',
        "<nodes>",
    ]
    for n in nodes:
        nid = id_map[n["id"]]
        label = escape(n.get("label", nid))
        score = n.get("score", 0)
        lines.append(
            f'<node id="{nid}" label="{label}">'
            f'<attvalues><attvalue for="score" value="{score}"/>'
            f'<attvalue for="url" value="{escape(n["id"])}"/></attvalues></node>'
        )
    lines.append("</nodes><edges>")
    for i, e in enumerate(edges):
        s, t = id_map.get(e["source"]), id_map.get(e["target"])
        if not s or not t:
            continue
        lines.append(f'<edge id="{i}" source="{s}" target="{t}" weight="1"/>')
    lines.extend(["</edges>", "</graph>", "</gexf>"])
    path.write_text("\n".join(lines), encoding="utf-8")


def export_link_graph_graphml(report: CrawlReport, path: Path, *, max_nodes: int = 800) -> None:
    data = build_link_graph_data(report, max_nodes=max_nodes, edge_cap=5000, node_cap=max_nodes)
    ns = "http://graphml.graphdrawing.org/xmlns"
    root = ET.Element("graphml", xmlns=ns)
    ET.SubElement(root, "key", id="d0", **{"for": "node"}, **{"attr.name": "label"}, **{"attr.type": "string"})
    graph = ET.SubElement(root, "graph", edgedefault="directed")
    id_map: dict[str, str] = {}
    for i, n in enumerate(data["nodes"]):
        nid = f"n{i}"
        id_map[n["id"]] = nid
        node = ET.SubElement(graph, "node", id=nid)
        d = ET.SubElement(node, "data", key="d0")
        d.text = n.get("label", n["id"])
    for e in data["edges"]:
        s, t = id_map.get(e["source"]), id_map.get(e["target"])
        if s and t:
            ET.SubElement(graph, "edge", source=s, target=t)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


_UI_WEBGL = Path(__file__).resolve().parent / "ui" / "link_graph_webgl.html"


def export_link_graph_webgl_html(report: CrawlReport, path: Path, *, max_nodes: int = 600) -> None:
    data = build_link_graph_data(report, max_nodes=max_nodes, edge_cap=4000, node_cap=800)
    template = _UI_WEBGL.read_text(encoding="utf-8")
    pages_css = report_styles_bundle()
    graph_css = load_ui_css("link-graph.css")
    html = (
        template.replace("{{REPORT_PAGES_CSS}}", pages_css)
        .replace("{{LINK_GRAPH_CSS}}", graph_css)
        .replace(
            "{{REPORT_NAV}}",
            report_topbar(path.parent, "內鏈圖", active="link_graph.html", site_url=report.start_url),
        )
        .replace("{{SITE_URL}}", escape(report.start_url))
        .replace("{{DATA_JSON}}", __import__("json").dumps(data, ensure_ascii=False))
        .replace("{{NODE_COUNT}}", str(len(data["nodes"])))
        .replace("{{EDGE_COUNT}}", str(len(data["edges"])))
    )
    path.write_text(html, encoding="utf-8")
