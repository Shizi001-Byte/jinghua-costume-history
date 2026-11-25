#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一手性缺口台账 primary_ledger.py  —— 第 1441 轮创建

目的：把「出处分级」从历轮笔记里的手写账，变成从 data/statute_library.json 现算的台账。
它要治三个具体的病（都是前面几十轮真踩过的）：

  病一：level 不在 statutes 顶层，而在 attribution.level。
        直接 s.get('level') 全返回 None，于是"7 条 secondary"只能靠记忆抄。
  病二：轮次号（1438／1439）与公元年份同落在 13xx–15xx 区间，
        简单正则 `1[3-5]\\d{2}` 会把轮次号当成年份节点，节点集合被污染。
  病三：汉字纪年（"洪武十四年定"）与公元纪年混写。
        只抽 4 位数字会漏掉 T2／T9 这类整条只有汉字纪年的条目，抽出空表。

用法（纯只读，不改库）：
  python3 primary_ledger.py            # 终端摘要
  python3 primary_ledger.py --json     # 结构化输出
  python3 primary_ledger.py --check    # 自洽断言，有 fail 则退出码 1
  python3 primary_ledger.py --write    # 另生成 md 台账到 knowledge_base/明代服饰/
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "data" / "statute_library.json"
OUT_MD = ROOT / "knowledge_base" / "明代服饰" / "一手性缺口台账_1441.md"

ALLOWED_LEVEL = {"primary_verified", "secondary_only"}

# 一手证据标记（出现即视为该节点有一手支撑）
PRIMARY_MARKS = ["实录卷", "实录卷次", "逐字核", "一手", "已核", "取一手"]
# 二手/缺口标记
GAP_MARKS = ["二手", "无一手", "实录不收", "实录本就不收", "未收", "无文", "无记载",
             "未取得", "缺卷", "待补卷", "待逐卷"]

CN_DIGIT = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9}


def cn2int(s: str):
    """汉字数（1–99 级）转整数；'元' 视为 1。失败返回 None。"""
    if s in ("元",):
        return 1
    if s.isdigit():
        return int(s)
    total, cur = 0, 0
    for ch in s:
        if ch in CN_DIGIT:
            cur = CN_DIGIT[ch]
        elif ch == "十":
            total += (cur or 1) * 10
            cur = 0
        elif ch in ("廿", "卅"):
            total += (20 if ch == "廿" else 30)
            cur = 0
        else:
            return None
    return total + cur


def extract_nodes(text: str, era_map: dict, field: str):
    """从一段文本抽「年份节点」。返回 list[dict(year, form, snippet, field)]。"""
    nodes = []
    # 1) 汉字纪年：年号 + 年数 + 「年」
    era_names = "|".join(sorted(era_map.keys(), key=len, reverse=True))
    pat_cn = re.compile(rf"({era_names})(元|[〇一二三四五六七八九十廿卅]{{1,3}})年")
    for m in pat_cn.finditer(text):
        n = cn2int(m.group(2))
        if not n:
            continue
        y = era_map[m.group(1)] + n - 1
        nodes.append({"year": y, "form": "汉字", "raw": m.group(0),
                      "field": field, "pos": m.start()})
    # 2) 公元纪年，排除轮次号
    pat_ad = re.compile(r"(?<![0-9])(1[3-5][0-9]{2})(?![0-9])")
    for m in pat_ad.finditer(text):
        y = int(m.group(1))
        win = text[max(0, m.start() - 8): m.end() + 6]
        # 轮次号污染：第1xxx次／1xxx轮
        if "第" in text[max(0, m.start() - 3): m.start()] and "次" in text[m.end(): m.end() + 3]:
            continue
        if "轮" in win and "轮次" in win:
            continue
        if "唤醒" in win:
            continue
        # 轮次号污染：第1438次／1438 轮／1439 复核／1440 段／…次唤醒
        head = text[max(0, m.start() - 3):m.start()]
        tail = text[m.end(): m.end() + 6]
        if ("次" in tail[:2] and "第" in head) or any(
                k in tail for k in ("轮", "段", "复核", "唤醒", "笔记", "次唤醒")) \
                or ".md" in text[max(0, m.start() - 10): m.end() + 8]:
            # 最后一条：产物文件名里的轮次号（如 …_节点补证_1438.md）
            continue
        nodes.append({"year": y, "form": "公元", "raw": m.group(0),
                      "field": field, "pos": m.start()})
    return nodes


def T(x) -> str:
    """把任意字段（str/list/dict/None）安全转成可搜索文本。"""
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, (list, tuple)):
        return "\n".join(T(i) for i in x)
    if isinstance(x, dict):
        return json.dumps(x, ensure_ascii=False)
    return str(x)


def marks_of(text: str):
    return {"primary": any(k in text for k in PRIMARY_MARKS),
            "gap": any(k in text for k in GAP_MARKS)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    d = json.loads(LIB.read_text(encoding="utf-8"))
    era_map = d["era_map"]
    rows, fails, warns = [], [], []

    for s in d["statutes"]:
        a = s.get("attribution") or {}
        if not isinstance(a, dict):
            a = {"level": None, "note": T(a)}
        level = a.get("level")
        note = T(a.get("note"))
        ysn = T(s.get("year_source_note"))
        src = T(s.get("source"))
        rev = T(s.get("revisions"))

        # 主节点只看叙述性两字段（note / ysn）；source 与 revisions 里的年份
        # 多为交叉引用或转录标注，单列 cited_years，不进 year_ce 校验
        nodes = []
        for text, fld in ((note, "attribution.note"), (ysn, "year_source_note"),
                          (T(s.get("era_year")), "era_year")):
            nodes += extract_nodes(text, era_map, fld)
        cited = []
        for text, fld in ((src, "source"), (rev, "revisions")):
            cited += extract_nodes(text, era_map, fld)

        # 去重：同一年份保留首现（汉字形式优先保留，因为它自带纪年）
        uniq = {}
        for n in nodes:
            key = n["year"]
            prev = uniq.get(key)
            if prev is None:
                uniq[key] = n
            elif prev["form"] == "公元" and n["form"] == "汉字":
                uniq[key] = n
        node_years = sorted(uniq.keys())

        cited_years = sorted({c["year"] for c in cited} - set(uniq.keys()))
        row = {
            "cited_years": cited_years,
            "id": s["id"], "title": s.get("title", ""), "level": level,
            "year_source": s.get("year_source"), "year_ce": s.get("year_ce"),
            "era_year": s.get("era_year"),
            "node_years": node_years,
            "nodes": [{"year": k, "form": uniq[k]["form"], "raw": uniq[k]["raw"],
                       "field": uniq[k]["field"],
                       "marks": marks_of(note + ysn + src)} for k in node_years],
            "note_marks": marks_of(note),
            "status": s.get("status"),
        }
        rows.append(row)

        # --- 断言 ---
        if level is None:
            fails.append(f"{s['id']} attribution.level 缺失")
        elif level not in ALLOWED_LEVEL:
            fails.append(f"{s['id']} attribution.level 越界: {level}")

        if level == "secondary_only":
            m = marks_of(note + T(a.get("means")))
            if len(note) < 12:
                warns.append(f"{s['id']} attribution.note 仅 {len(note)} 字（{note!r}），复核依据过薄，判词可能只在 means 里")
            row["note_marks"] = m
            if not (m["primary"] or m["gap"]):
                fails.append(f"{s['id']} secondary 但 note 无一手/二手判词（判词缺失=无法复核）")

        ce = s.get("year_ce")
        if ce is None:
            fails.append(f"{s['id']} year_ce 缺失")
        elif ce not in node_years:
            fails.append(f"{s['id']} year_ce={ce} 不在节点集合 {node_years}（纪年与叙述不一致）")

        if s.get("year_source") == "unknown" and len(node_years) >= 2:
            warns.append(f"{s['id']} year_source=unknown 但有 {len(node_years)} 个年份节点 "
                         f"{node_years}（'无源可依'与'源多无单一'混在同一取值）")

        if level == "primary_verified" and not any(
                k in (note + ysn + src) for k in ("实录卷", "逐字核", "一手")):
            warns.append(f"{s['id']} primary_verified 但三字段无一手标记字样（可能虚标）")

    # --- 汇总 ---
    from collections import Counter
    dist = Counter(r["level"] or "<missing>" for r in rows)
    sec = [r for r in rows if r["level"] == "secondary_only"]

    summary = {
        "total": len(rows),
        "level_dist": dict(dist),
        "secondary_ids": [r["id"] for r in sec],
        "secondary_count": len(sec),
        "fails": fails, "warns": warns,
        "generated_from": str(LIB),
    }

    if args.json:
        print(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2))
        return 0 if not fails else 1

    print(f"库: {LIB}  |  条目 {len(rows)}  |  level 分布 {dict(dist)}")
    print(f"secondary {len(sec)} 条: {[r['id'] for r in sec]}")
    print()
    print(f"{'id':4} {'level':17} {'ce':6} {'节点':5} 节点年份")
    for r in rows:
        print(f"{r['id']:4} {str(r['level']):17} {str(r['year_ce']):6} {len(r['node_years']):<5} {r['node_years']}")
    print()
    if fails:
        print("【FAIL】")
        for f in fails:
            print("  ✗", f)
    else:
        print("【FAIL】无")
    if warns:
        print("【WARN】")
        for w in warns:
            print("  ⚠", w)
    else:
        print("【WARN】无")

    if args.write:
        write_md(rows, summary)
        print(f"\n已写台账: {OUT_MD}")

    return 0 if not fails else 1


def write_md(rows, summary):
    lines = []
    lines.append("# 一手性缺口台账（1441 轮·脚本现算）\n")
    lines.append("> 由 `primary_ledger.py --write` 生成，**不要手改**；改库或改脚本后重跑即可。\n")
    lines.append(f"> 数据源：`data/statute_library.json`（条目 {summary['total']} 条）\n")
    lines.append("\n## 一、结论先说\n")
    lines.append(f"- level 分布：{summary['level_dist']}。**level 在 `attribution.level`，不在 statutes 顶层**——"
                 "直接 `get('level')` 会全返回 None，这是历轮靠记忆抄数的病根。\n")
    lines.append(f"- `secondary_only` 共 **{summary['secondary_count']}** 条：{', '.join(summary['secondary_ids'])}。\n")
    lines.append("- 它们不是同一类缺口，按「缺的是系年还是形制」分三类（逐条见第二节）："
                 "①实录不收（无源可依）②形制无一手（系年有一手）③源多无单一（无单一纪年源）。\n")
    if summary["warns"]:
        lines.append("\n**脚本警告**\n")
        for w in summary["warns"]:
            lines.append(f"- ⚠ {w}\n")
    if summary["fails"]:
        lines.append("\n**断言失败**\n")
        for f in summary["fails"]:
            lines.append(f"- ✗ {f}\n")

    lines.append("\n## 二、逐条节点表\n")
    for r in rows:
        tag = "★" if r["level"] == "secondary_only" else ""
        lines.append(f"### {tag} {r['id']} {r['title']}\n")
        lines.append(f"- level：`{r['level']}` ｜ year_source：`{r['year_source']}` ｜ "
                     f"year_ce：{r['year_ce']} ｜ era_year：{r['era_year']} ｜ status：`{r['status']}`\n")
        lines.append(f"- 一手判词：note {'有' if r['note_marks']['primary'] else '无'} ｜ "
                     f"缺口判词：note {'有' if r['note_marks']['gap'] else '无'}\n")
        if r["cited_years"]:
            lines.append(f"- 引用年份（source/revisions，仅供参考不计节点）：{r['cited_years']}\n")
        if r["node_years"]:
            lines.append("\n| 年份 | 形式 | 原文 | 出自字段 |\n|---|---|---|---|\n")
            for n in r["nodes"]:
                lines.append(f"| {n['year']} | {n['form']} | `{n['raw']}` | {n['field']} |\n")
        else:
            lines.append("- 未从 note/ysn/source/revisions 抽到任何年份节点（该条可能整条无纪年）。\n")
        lines.append("\n")

    lines.append("\n## 三、口径声明\n")
    lines.append("- 节点年份由正则抽取，**不等于**该年有第一手证据；是否一手要看 `attribution.note`／`year_source_note` 的逐字核记录。\n")
    lines.append("- 汉字纪年按库内 `era_map` 换算（如「洪武十四年定」→1381）。若年号元年本身错，节点全错——era_map 自身另须审计。\n")
    lines.append("- 公元年份抽取已排除「第1xxx次」「1xxx轮」「唤醒」上下文，防止轮次号被当节点（1438/1439 曾污染 T19 节点集合）。\n")
    lines.append("- 本台账只读库、不改库；`--check` 的 fail 项须人工复核后改库，不自动修。\n")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
