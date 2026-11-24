#!/usr/bin/env python3
"""Publish only new openings that meet an explicit, fail-closed source and data policy."""
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
JST = timezone(timedelta(hours=9))
ALLOWED_MUNICIPALITIES = {
    "下関市", "宇部市", "山口市", "萩市", "防府市", "下松市", "岩国市",
    "光市", "長門市", "柳井市", "美祢市", "周南市", "山陽小野田市",
    "周防大島町", "和木町", "上関町", "田布施町", "平生町", "阿武町",
}

def read_json(name, default):
    path = DATA / name
    if not path.exists():
        return default
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{name}: JSON root must be an object")
    return value

def parse_date(value):
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except (TypeError, ValueError):
        return None

def host_of(url):
    try:
        parsed = urlsplit(str(url or "").strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            return ""
        return host
    except ValueError:
        return ""

def allowed_host(url, domains):
    host = host_of(url)
    return bool(host and any(host == d or host.endswith("." + d) for d in domains))

def eligible_reasons(draft, config, today=None):
    """Return reasons for holding a candidate; empty means every gate passed."""
    today = today or datetime.now(JST).date()
    reasons = []
    categories = draft.get("category", [])
    if isinstance(categories, str):
        categories = [categories]
    if categories != ["新店・開店"]:
        reasons.append("新店・開店だけの候補ではない")
    if draft.get("content_type") != "店舗・商業施設":
        reasons.append("店舗・商業施設として確定していない")
    if draft.get("status") != "未確認・公開禁止":
        reasons.append("候補の公開禁止ステータスが不正")
    if draft.get("manual_hold") is True:
        reasons.append("手動保留フラグあり")
    if draft.get("review_flags"):
        reasons.append("確認フラグあり")
    if draft.get("duplicate_review") or draft.get("duplicate_candidate_ids"):
        reasons.append("重複確認が必要")
    if draft.get("freshness") != "直近30日":
        reasons.append("記事の鮮度が直近30日ではない")
    store_name = str(draft.get("store_name") or "").strip()
    address = str(draft.get("address") or "").strip()
    name_candidates = draft.get("store_name_candidates")
    if (
        draft.get("store_name_extraction_status") != "単一候補"
        or not isinstance(name_candidates, list)
        or len(name_candidates) != 1
        or str(name_candidates[0]).strip() != store_name
    ):
        reasons.append("店舗名が本文から一意に抽出できていない")
    address_candidates = draft.get("address_candidates")
    if (
        draft.get("address_extraction_status") != "住所形式を抽出"
        or not isinstance(address_candidates, list)
        or len(address_candidates) != 1
        or str(address_candidates[0]).strip() != address
    ):
        reasons.append("住所が本文から一意に抽出できていない")
    if draft.get("opening_status_evidence") not in ("実施済み表現あり", "予定表現あり"):
        reasons.append("開店の実施・予定を示す明確な表現がない")
    if len(store_name) < 2:
        reasons.append("店舗名の明示データがない")
    if len(address) < 8 or not any(x in address for x in ALLOWED_MUNICIPALITIES):
        reasons.append("山口県内の市町名を含む住所の明示データがない")
    municipality = str(draft.get("municipality") or "").strip()
    if municipality not in ALLOWED_MUNICIPALITIES:
        reasons.append("所在地の市町が確定していない")
    if address and municipality and not address.startswith("山口県" + municipality):
        reasons.append("住所と市町名が一致していない")
    if not draft.get("opening_action_evidence"):
        reasons.append("開店を示す動作語が確認できない")
    if not draft.get("body_excerpt") or len(str(draft.get("body_excerpt"))) < 40:
        reasons.append("本文根拠が不足")
    if not draft.get("source_url"):
        reasons.append("主出典URLがない")
    domains = config.get("allowed_domains", [])
    if not isinstance(domains, list) or not domains:
        reasons.append("店舗公式情報源の許可ドメインが未設定")
    else:
        domains = [str(x).lower().strip().rstrip(".") for x in domains if str(x).strip()]
        if not allowed_host(draft.get("source_url"), domains):
            reasons.append("主出典が許可済み公式ドメインではない")
    # 自動公開の根拠にできるのは主出典だけ。まとめサイト・地域メディア等の
    # 補助出典が混在しても、それらを根拠にせず、主出典の公式性と正常性を個別確認する。
    primary_url = str(draft.get("source_url") or "").strip()
    sources = draft.get("source_urls")
    if not isinstance(sources, list) or not sources:
        reasons.append("出典一覧がない")
    elif not any(
        isinstance(source, dict)
        and str(source.get("url") or "").strip() == primary_url
        for source in sources
    ):
        reasons.append("主出典が出典一覧に含まれていない")
    checks = draft.get("source_link_checks")
    if not isinstance(checks, list) or not checks:
        reasons.append("主出典URLの正常確認記録がない")
    else:
        checked = {
            str(x.get("url") or "").strip(): x
            for x in checks if isinstance(x, dict)
        }
        primary_check = checked.get(primary_url, {})
        if (
            not primary_url
            or primary_check.get("status") != "ok"
            or not allowed_host(primary_check.get("final_url"), domains)
        ):
            reasons.append("主出典URLが正常確認済みで、転送先も許可済み公式ドメインではない")
    published = parse_date(draft.get("published_date"))
    event = parse_date(draft.get("event_date"))
    if not published or (today - published).days < 0 or (today - published).days > 30:
        reasons.append("記事公開日が直近30日以内の有効日付ではない")
    if not event or (event - today).days > 60 or (today - event).days > 7:
        reasons.append("開店日が不明、または対象期間外")
    if event and draft.get("opening_status_evidence") == "実施済み表現あり" and event > today:
        reasons.append("実施済み表現と未来の開店日が矛盾")
    if event and draft.get("opening_status_evidence") == "予定表現あり" and event < today:
        reasons.append("開店予定表現と過去の開店日が矛盾")
    if not re.match(r"^https://", str(draft.get("source_url") or "")):
        reasons.append("主出典URLがHTTPSではない")
    return list(dict.fromkeys(reasons))

def main():
    drafts = read_json("drafts.json", {"drafts": []}).get("drafts", [])
    published = read_json("published.json", {"updated_at": "", "articles": []})
    config = read_json("auto_opening_sources.json", {"allowed_domains": []})
    if not isinstance(drafts, list) or not isinstance(published.get("articles"), list):
        raise SystemExit("候補または公開データの形式が不正です。自動公開を中止しました")
    existing = {str(x.get("id")): x for x in published["articles"] if isinstance(x, dict) and x.get("id")}
    now = datetime.now(JST).isoformat()
    added = 0
    held = 0
    hold_reason_counts = {}
    for draft in drafts:
        if not isinstance(draft, dict) or not draft.get("id"):
            continue
        aid = str(draft["id"])
        if aid in existing:
            continue
        reasons = eligible_reasons(draft, config)
        if reasons:
            # Candidate remains unpublished and available for human review.
            held += 1
            for reason in reasons:
                hold_reason_counts[reason] = hold_reason_counts.get(reason, 0) + 1
            print(f"自動公開保留: {aid} / " + "、".join(reasons))
            continue
        event = parse_date(draft["event_date"])
        article = dict(draft)
        article.update({
            "title": str(draft["store_name"]).strip() + "が" + ("オープン予定" if event > datetime.now(JST).date() else "オープン"),
            "store_name": str(draft["store_name"]).strip(),
            "address": str(draft["address"]).strip(),
            "municipality": str(draft["municipality"]).strip(),
            "area": [str(draft["municipality"]).strip()],
            "municipality_group": str(draft["municipality"]).strip(),
            "municipality_status": "公式情報で確認済み",
            "business_status": "開店予定" if event > datetime.now(JST).date() else "営業中",
            "body": str(draft["body_excerpt"]).strip(),
            "summary": str(draft["body_excerpt"]).strip()[:180],
            "body_excerpt": str(draft["body_excerpt"]).strip()[:180],
            "review_flags": [],
            "status": "公開済み",
            "published_at": now,
            "approved_at": now,
            "auto_publication": {
                "type": "new_opening",
                "policy_version": 1,
                "source_domains": [host_of(draft.get("source_url"))],
                "published_at": now,
            },
        })
        article.pop("review_flags", None)
        existing[aid] = article
        added += 1
        print(f"新規オープン自動公開: {aid}")
    if added:
        published["articles"] = sorted(existing.values(), key=lambda x: (x.get("published_date", ""), x.get("title", "")), reverse=True)
        published["updated_at"] = now
        (DATA / "published.json").write_text(json.dumps(published, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"新規オープン自動公開: {added}件 / 条件不足で保留: {held}件")
    if hold_reason_counts:
        print("保留理由別件数:")
        for reason, count in sorted(hold_reason_counts.items(), key=lambda item: (-item[1], item[0])):
            print(f"- {reason}: {count}件")
    if added == 0:
        print("自動公開対象はありません。条件不足の候補は人による確認待ちのままです。")

if __name__ == "__main__":
    main()
