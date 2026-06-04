"""AI 潤飾用量配額。"""

from pathlib import Path

from sitespider.plans import get_plan
from sitespider.usage import (
    add_ai_polish_bonus,
    check_ai_polish_quota,
    effective_ai_polish_limit,
    record_ai_polish,
    tenant_usage,
    usage_limits_json,
)


def test_ai_quota_pro(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    plan = get_plan("pro")
    q = check_ai_polish_quota("t1", plan)
    assert q.allowed
    assert q.ai_limit == 15
    for _ in range(15):
        record_ai_polish("t1")
    q2 = check_ai_polish_quota("t1", plan)
    assert not q2.allowed
    assert tenant_usage("t1")["ai_polishes"] == 15


def test_ai_quota_starter_one_per_month(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    plan = get_plan("starter")
    q = check_ai_polish_quota("t1", plan)
    assert q.allowed
    assert q.ai_limit == 1
    record_ai_polish("t1")
    q2 = check_ai_polish_quota("t1", plan)
    assert not q2.allowed
    assert "上限" in q2.reason


def test_ai_bonus_increases_limit(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    plan = get_plan("pro")
    add_ai_polish_bonus("t1", 5)
    u = tenant_usage("t1")
    assert effective_ai_polish_limit(plan, u) == 20
    lim = usage_limits_json(plan, u)
    assert lim["ai_polish_bonus"] == 5
    assert lim["ai_polishes_remaining"] == 20


def test_free_plan_pages(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from sitespider.usage import check_crawl_quota

    p = get_plan("free")
    assert p.max_pages_per_crawl == 50
    q = check_crawl_quota("t1", p, pages_requested=50)
    assert q.allowed
    q2 = check_crawl_quota("t1", p, pages_requested=51)
    assert not q2.allowed
