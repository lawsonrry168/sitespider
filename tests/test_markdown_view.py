"""Markdown HTML 預覽。"""

from sitespider.markdown_view import markdown_page_html, render_markdown_html


def test_render_links_and_headings():
    html = render_markdown_html("# Title\n\n**bold** [link](x.html)\n")
    assert "<h1>Title</h1>" in html
    assert "<strong>bold</strong>" in html
    assert 'href="x.html"' in html


def test_markdown_page_wraps_theme():
    page = markdown_page_html("# Hi\n", title="交付導覽")
    assert "<!DOCTYPE html>" in page
    assert "交付導覽" in page
    assert "<h1>Hi</h1>" in page
