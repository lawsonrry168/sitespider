from pathlib import Path

from sitespider.crawler import CrawlReport, PageResult
from sitespider.link_graph import build_link_graph_data, export_link_graph_html
from sitespider.ngrams import collect_ngrams, export_ngrams_csv
from sitespider.spelling_check import collect_spelling_rows, export_spelling_csv


def _page(url: str, **kw) -> PageResult:
    defaults = dict(
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Best beauty products online",
        meta_description="Shop the best beauty products for your skin care routine",
        meta_robots=None,
        h1=["Beauty Products"],
        canonical=url,
    )
    defaults.update(kw)
    return PageResult(url=url, **defaults)


def test_ngrams_collects_bigrams():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = _page("https://x/a")
    report.pages["https://x/b"] = _page("https://x/b", title="Best beauty products online")
    rows = collect_ngrams(report, min_count=1)
    phrases = {r["Phrase"] for r in rows}
    assert "best beauty" in phrases or "beauty products" in phrases


def test_spelling_flags_unknown_word(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = _page(
        "https://x/a",
        title="Zzzqxv beauty spa",
        meta_description="Welcome",
    )
    rows = collect_spelling_rows(report)
    words = {r["Word"].lower() for r in rows}
    assert "zzzqxv" in words
    out = tmp_path / "spelling.csv"
    export_spelling_csv(report, out)
    text = out.read_text(encoding="utf-8-sig")
    assert "Zzzqxv" in text
    assert "Engine" in text


def test_link_graph_nodes(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    a, b = "https://x/a", "https://x/b"
    from sitespider.crawler import LinkInfo

    report.pages[a] = _page(a)
    report.pages[b] = _page(b, title="Page B")
    report.pages[a].links = [
        LinkInfo(href="/b", resolved=b, text="go", link_type="internal", nofollow=False)
    ]
    report.pages[b].inlinks = [a]
    data = build_link_graph_data(report, max_nodes=10)
    assert data["nodes"]
    export_link_graph_html(report, tmp_path / "link_graph.html")
    html = (tmp_path / "link_graph.html").read_text(encoding="utf-8")
    assert "d3.min.js" in html or "互動" in html


def test_export_ngrams_csv(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = _page("https://x/a")
    export_ngrams_csv(report, tmp_path / "ngrams.csv")
    text = (tmp_path / "ngrams.csv").read_text(encoding="utf-8-sig")
    assert "Phrase" in text
