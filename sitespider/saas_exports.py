"""依訂閱方案產生 Pro / Agency 進階匯出。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sitespider.plans import Plan, get_plan

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def export_plan_features(
    report: CrawlReport,
    out_dir: Path,
    *,
    plan_id: str | None = None,
    tenant_id: str = "default",
    base: Path | None = None,
) -> tuple[list[str], int]:
    """
    回傳 (新增檔名列表, serp API 查詢次數)。
    """
    plan: Plan = get_plan(plan_id)
    written: list[str] = []
    serp_queries = 0

    if plan.has("gexf"):
        from sitespider.link_export import export_link_graph_gexf, export_link_graph_graphml

        export_link_graph_gexf(report, out_dir / "link_graph.gexf", max_nodes=800)
        export_link_graph_graphml(report, out_dir / "link_graph.graphml", max_nodes=800)
        written.extend(["link_graph.gexf", "link_graph.graphml"])

    if plan.has("webgl"):
        from sitespider.link_export import export_link_graph_webgl_html

        export_link_graph_webgl_html(report, out_dir / "link_graph_webgl.html", max_nodes=600)
        written.append("link_graph_webgl.html")

    if plan.has("serp_rank"):
        from sitespider.serp_rank import export_serp_rank_csv, serpapi_available
        from sitespider.usage import check_serp_quota

        max_q = min(15, plan.max_serp_queries_per_month)
        if serpapi_available() and check_serp_quota(tenant_id, plan, max_q, base):
            serp_queries = export_serp_rank_csv(
                report, out_dir / "serp_rank.csv", max_queries=max_q
            )
            written.append("serp_rank.csv")

    return written, serp_queries
