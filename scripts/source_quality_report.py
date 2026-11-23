import json
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data" / "drafts.json"
OUTPUT = ROOT / "data" / "source_quality_report.json"


def source_names_for(draft):
    rows = draft.get("source_urls")
    names = []
    if isinstance(rows, list):
        names.extend(
            str(row.get("source_name") or "").strip()
            for row in rows if isinstance(row, dict)
        )
    names.append(str(draft.get("source_name") or "").strip())
    names = list(dict.fromkeys(name for name in names if name))
    return names or ["情報源不明"]


def build_source_quality_report(drafts):
    """Measure collection/link completeness, not factual accuracy or trustworthiness."""
    groups = {}
    for draft in drafts:
        if not isinstance(draft, dict):
            continue
        names = source_names_for(draft)
        checks = draft.get("source_link_checks")
        checks = checks if isinstance(checks, list) else []
        for name in names:
            group = groups.setdefault(name, {
                "candidate_ids": set(),
                "candidates": 0,
                "published_date": 0,
                "event_date": 0,
                "body_excerpt": 0,
                "review_flagged": 0,
                "link_status": Counter(),
                "links": 0,
            })
            candidate_id = str(draft.get("id") or id(draft))
            if candidate_id not in group["candidate_ids"]:
                group["candidate_ids"].add(candidate_id)
                group["candidates"] += 1
                group["published_date"] += bool(str(draft.get("published_date") or "").strip())
                group["event_date"] += bool(str(draft.get("event_date") or "").strip())
                group["body_excerpt"] += bool(str(draft.get("body_excerpt") or "").strip())
                group["review_flagged"] += bool(draft.get("review_flags"))
            source_checks = [
                item for item in checks
                if isinstance(item, dict) and str(item.get("source_name") or "").strip() == name
            ]
            source_rows = draft.get("source_urls")
            source_rows = source_rows if isinstance(source_rows, list) else []
            expected_urls = {
                str(row.get("url") or "").strip()
                for row in source_rows
                if isinstance(row, dict) and str(row.get("source_name") or "").strip() == name
                and str(row.get("url") or "").strip()
            }
            if str(draft.get("source_name") or "").strip() == name and draft.get("source_url"):
                expected_urls.add(str(draft["source_url"]).strip())
            recorded_urls = set()
            for check in source_checks:
                status = str(check.get("status") or "unknown")
                group["link_status"][status] += 1
                group["links"] += 1
                if check.get("url"):
                    recorded_urls.add(str(check["url"]).strip())
            missing_checks = len(expected_urls - recorded_urls)
            if missing_checks:
                group["link_status"]["not_recorded"] += missing_checks
                group["links"] += missing_checks

    sources = []
    for name, group in sorted(groups.items()):
        total = group["candidates"]
        def rate(count):
            return round(count * 100 / total, 1) if total else None
        links = group["links"]
        statuses = dict(sorted(group["link_status"].items()))
        sources.append({
            "name": name,
            "candidate_count": total,
            "published_date_coverage_percent": rate(group["published_date"]),
            "event_date_coverage_percent": rate(group["event_date"]),
            "body_excerpt_coverage_percent": rate(group["body_excerpt"]),
            "review_flag_rate_percent": rate(group["review_flagged"]),
            "link_check_count": links,
            "link_status_counts": statuses,
            "broken_link_count": statuses.get("broken", 0),
            "inconclusive_link_count": statuses.get("inconclusive", 0),
            "unchecked_link_count": statuses.get("not_checked_limit", 0) + statuses.get("not_recorded", 0),
        })
    return {
        "candidate_count": sum(item["candidate_count"] for item in sources),
        "source_count": len(sources),
        "sources": sources,
        "scope_note": "収集・記載・URL到達性の観測値です。情報源の信頼性、記事内容の正確性、店舗情報の真偽を評価・保証するものではありません。",
    }


def render_markdown(report):
    lines = [
        "## 情報源別の収集品質レポート",
        "",
        "| 情報源 | 候補 | 公開日 | 動作日 | 本文 | 要確認フラグ | URL確認 | 404/410 | 確認不能 | 未確認 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in report["sources"]:
        links = item["link_status_counts"]
        lines.append(
            f"| {item['name']} | {item['candidate_count']} | "
            f"{item['published_date_coverage_percent']}% | "
            f"{item['event_date_coverage_percent']}% | "
            f"{item['body_excerpt_coverage_percent']}% | "
            f"{item['review_flag_rate_percent']}% | "
            f"{item['link_check_count']} | {item['broken_link_count']} | "
            f"{item['inconclusive_link_count']} | {item['unchecked_link_count']} |"
        )
    lines += ["", report["scope_note"]]
    return "\n".join(lines)


def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    drafts = data.get("drafts", [])
    if not isinstance(drafts, list):
        raise SystemExit("Invalid drafts schema: drafts must be an array")
    report = build_source_quality_report(drafts)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(markdown + "\n")
    print(markdown)


if __name__ == "__main__":
    main()
