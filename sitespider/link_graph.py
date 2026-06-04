"""
內鏈視覺化：互動 D3 力導向圖 + 簡易 SVG 示意。
"""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

from sitespider.link_metrics import collect_internal_inlinks, compute_page_link_stats
from sitespider.report_theme import load_ui_css, report_styles_bundle, report_topbar

_UI_INTERACTIVE = Path(__file__).resolve().parent / "ui" / "link_graph_interactive.html"


def _graph_css_bundle() -> tuple[str, str]:
    return report_styles_bundle(), load_ui_css("link-graph.css")


def _fill_graph_template(
    template: str,
    out_dir: Path,
    report: CrawlReport,
    *,
    page_title: str,
    active: str,
    **replacements: str,
) -> str:
    pages_css, graph_css = _graph_css_bundle()
    html = (
        template.replace("{{REPORT_PAGES_CSS}}", pages_css)
        .replace("{{LINK_GRAPH_CSS}}", graph_css)
        .replace(
            "{{REPORT_NAV}}",
            report_topbar(out_dir, page_title, active=active, site_url=report.start_url),
        )
    )
    for key, val in replacements.items():
        html = html.replace("{{" + key + "}}", val)
    return html


def _short_label(url: str, max_len: int = 28) -> str:
    path = urlparse(url).path or "/"
    if len(path) <= max_len:
        return path
    return "…" + path[-(max_len - 1) :]


def build_link_graph_data(
    report: CrawlReport,
    *,
    max_nodes: int = 150,
    edge_cap: int = 800,
    node_cap: int = 200,
) -> dict:
    cap = node_cap
    stats = compute_page_link_stats(report)
    ranked = sorted(
        report.pages.keys(),
        key=lambda u: (
            stats.get(u).link_score if stats.get(u) else 0,
            stats.get(u).inlinks if stats.get(u) else 0,
        ),
        reverse=True,
    )
    nodes = ranked[:max_nodes]
    node_set = set(nodes)
    edges: list[dict] = []
    for row in collect_internal_inlinks(report):
        if row.source in node_set and row.destination in node_set:
            edges.append(
                {
                    "source": row.source,
                    "target": row.destination,
                    "anchor": (row.anchor or "")[:60],
                    "nofollow": bool(row.nofollow),
                }
            )
    seen_e: set[tuple[str, str]] = set()
    unique_edges: list[dict] = []
    for e in edges:
        key = (e["source"], e["target"])
        if key in seen_e:
            continue
        seen_e.add(key)
        unique_edges.append(e)

    node_payload = []
    for url in nodes:
        st = stats.get(url)
        node_payload.append(
            {
                "id": url,
                "label": _short_label(url),
                "score": round(st.link_score, 4) if st else 0,
                "inlinks": st.inlinks if st else 0,
            }
        )
    return {
        "nodes": node_payload,
        "edges": unique_edges[:edge_cap],
        "max_nodes_cap": min(max(len(ranked), 20), cap),
    }


def export_link_graph_full_html(report: CrawlReport, path: Path) -> None:
    """全站大型內鏈圖（最多 500 節點）。"""
    n = len(report.pages)
    max_nodes = min(max(n, 50), 500)
    data = build_link_graph_data(
        report,
        max_nodes=max_nodes,
        edge_cap=2500,
        node_cap=500,
    )
    cap = data.pop("max_nodes_cap", 500)
    node_count = len(data["nodes"])
    template = _UI_INTERACTIVE.read_text(encoding="utf-8")
    html = _fill_graph_template(
        template,
        path.parent,
        report,
        page_title="內鏈圖（全站）",
        active="link_graph.html",
        SITE_URL=escape(report.start_url),
        DATA_JSON=json.dumps(data, ensure_ascii=False),
        NODE_COUNT=str(node_count),
        EDGE_COUNT=str(len(data["edges"])),
        MAX_NODES=str(cap),
        GRAPH_TITLE="內鏈互動圖（全站）",
    )
    path.write_text(html, encoding="utf-8")


def export_link_graph_html(report: CrawlReport, path: Path, *, max_nodes: int = 120) -> None:
    """互動內鏈圖（D3）。"""
    data = build_link_graph_data(report, max_nodes=max(max_nodes, 20))
    cap = data.pop("max_nodes_cap", 150)
    node_count = len(data["nodes"])
    template = _UI_INTERACTIVE.read_text(encoding="utf-8")
    html = _fill_graph_template(
        template,
        path.parent,
        report,
        page_title="內鏈圖",
        active="link_graph.html",
        SITE_URL=escape(report.start_url),
        DATA_JSON=json.dumps(data, ensure_ascii=False),
        NODE_COUNT=str(node_count),
        EDGE_COUNT=str(len(data["edges"])),
        MAX_NODES=str(cap),
        GRAPH_TITLE="內鏈互動圖",
    )
    path.write_text(html, encoding="utf-8")


def export_link_graph_simple_html(report: CrawlReport, path: Path) -> None:
    """簡易環狀 SVG（無外部 JS）。"""
    data = build_link_graph_data(report, max_nodes=45)
    payload = json.dumps(
        {"nodes": data["nodes"], "edges": data["edges"][:200]},
        ensure_ascii=False,
    )
    n = len(data["nodes"]) or 1
    radius = 220
    cx, cy = 280, 280
    for i, node in enumerate(data["nodes"]):
        angle = 2 * math.pi * i / n
        node["x"] = cx + radius * math.cos(angle)
        node["y"] = cy + radius * math.sin(angle)

    pages_css, graph_css = _graph_css_bundle()
    topbar = report_topbar(
        path.parent, "內鏈圖（簡易）", active="link_graph.html", site_url=report.start_url
    )
    label = escape(report.start_url)

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Link Graph (Simple) — {label}</title>
  <style>
{pages_css}
{graph_css}
  </style>
</head>
<body>
  {topbar}
  <div class="graph-simple-wrap">
    <p class="lead">環狀 SVG 示意 · <a href="link_graph.html">互動版</a></p>
    <svg viewBox="0 0 560 560" id="graph" class="graph-svg-wrap"></svg>
  </div>
  <script>
  const DATA = {payload};
  const byId = Object.fromEntries(DATA.nodes.map(n => [n.id, n]));
  const svg = document.getElementById('graph');
  const ns = 'http://www.w3.org/2000/svg';
  DATA.edges.forEach(e => {{
    const s = byId[e.source], t = byId[e.target];
    if (!s || !t) return;
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('class', 'edge');
    line.setAttribute('x1', s.x); line.setAttribute('y1', s.y);
    line.setAttribute('x2', t.x); line.setAttribute('y2', t.y);
    svg.appendChild(line);
  }});
  DATA.nodes.forEach(n => {{
    const g = document.createElementNS(ns, 'g');
    g.setAttribute('transform', `translate(${{n.x}},${{n.y}})`);
    const c = document.createElementNS(ns, 'circle');
    c.setAttribute('r', 6 + Math.min(12, n.score * 40));
    const t = document.createElementNS(ns, 'text');
    t.setAttribute('y', 18); t.setAttribute('text-anchor', 'middle');
    t.setAttribute('fill', '#71717a'); t.setAttribute('font-size', '9');
    t.textContent = n.label;
    g.appendChild(c); g.appendChild(t);
    svg.appendChild(g);
  }});
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
