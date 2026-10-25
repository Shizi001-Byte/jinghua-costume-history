#!/usr/bin/env python3
"""
景华 · 法条年份自洽检查器（era_check）
第1044次唤醒（2026-10-25 00:20）新建

【它查什么】
法条库里每条都有两样东西：
  - era_year  年号原文（「洪武五年」「弘治元年」…）
  - year_ce   我写的公元年（1372）
它只做一件事：**用 era_map 把 era_year 换算成公元，和 year_ce 对不对得上。**

【它不查什么 —— 这是它的诚实边界】
换算对 ≠ 归属对。
T4 的全套材料都有：会典系于洪武二十四年，实录系于洪武五年。
**两边换算都没错，错的是「这条法条属于哪一年」这个史学判断。**
那一层不是可枚举的，需要实录/会典原文/出土实物。
所以这个检查器只能抓「公元算错」这种低级错——而低级错恰恰是最容易犯的。

【为什么只查低级错也值得】
T4 我四次改判，每一次都是年份。如果当时 year_ce 手滑写成 1391 或 1373，
没有这个检查器，我要靠再跑一遍四向验证才能发现——而我不一定跑。

用法：
  python3 era_check.py            # 查全部
  python3 era_check.py --selfcheck # 双向自测
退出码：0 一致 / 1 有错 / 2 自测失败
"""
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(BASE_DIR, "data", "statute_library.json")

# 汉数字 → 阿拉伯。**必须含「十」「二十」「二十六」这类复合**
# —— 第1042次我就是在这里覆盖了旧的 CN_NUM，把年号解析全搞挂。
CN_NUM = {
    "元": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
    "十六": 16, "十七": 17, "十八": 18, "十九": 19,
    "二十": 20, "二十一": 21, "二十二": 22, "二十三": 23, "二十四": 24,
    "二十五": 25, "二十六": 26, "二十七": 27, "二十八": 28, "二十九": 29,
    "三十": 30, "三十一": 31, "三十二": 32, "三十三": 33, "三十四": 34,
    "三十五": 35, "三十六": 36, "三十七": 37, "三十八": 38,
}


def parse_era(text, era_map):
    """从自由文本里抠出 (年号, 年数, 公元)。抠不到返回 None。
    长年号优先匹配，避免「洪武」吃掉「洪武二十六年」的一部分。"""
    if not text:
        return None
    eras = sorted(era_map.keys(), key=len, reverse=True)
    for era in eras:
        # 年号后面跟 汉数字+年
        m = re.search(re.escape(era) + r"([元一二三四五六七八九十]+)年", text)
        if m:
            num_s = m.group(1)
            n = CN_NUM.get(num_s)
            if n is None:
                continue
            return (era, num_s, era_map[era] + n - 1)
    return None


def check_lib(path=LIB, quiet=False):
    """返回 (errors, infos)。errors 是 [(sid, msg)]"""
    errors, infos = [], []
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        return [(("LIB"), f"读取失败 {e}")], []

    era_map = d.get("era_map") or {}
    if not era_map:
        return [(("LIB"), "era_map 缺失，无法换算")], []

    for s in d.get("statutes", []):
        sid = s.get("id", "?")
        era_year = s.get("era_year")
        year_ce = s.get("year_ce")

        if era_year is None:
            infos.append((sid, "无 era_year 字段，跳过换算"))
            continue
        if year_ce is None:
            errors.append((sid, "有 era_year 但 year_ce 为空"))
            continue

        got = parse_era(era_year, era_map)
        if got is None:
            infos.append((sid, f"era_year「{era_year}」里抠不出年号，无法换算"))
            continue

        era, num_s, calc = got
        if calc != year_ce:
            # 多值年号（「洪武五年（初定）/ 洪武二十四年」）会把第二段算进去，
            # 这里只比对第一段（对应 year_ce）；若第一段对不上才是真错。
            errors.append((sid, f"{era}{num_s}年 = {calc}，但 year_ce 写的 {year_ce}"
                                f"（差 {year_ce - calc} 年）"))
        else:
            infos.append((sid, f"{era}{num_s}年 = {year_ce} ✅"))

        # T16 那种「一字段两个量」：effective_by_occasion 里每个场合都要对
        ebo = s.get("effective_by_occasion")
        if isinstance(ebo, dict):
            for occ, v in ebo.items():
                if not isinstance(v, dict):
                    continue
                oc = parse_era(v.get("era", ""), era_map)
                oy = v.get("year_ce")
                if oc and oy and oc[2] != oy:
                    errors.append((sid, f"[{occ}] {oc[0]}{oc[1]}年 = {oc[2]}，"
                                        f"但写的 {oy}（差 {oy - oc[2]} 年）"))
                elif oc and oy:
                    infos.append((sid, f"[{occ}] {oc[0]}{oc[1]}年 = {oy} ✅"))

    if not quiet:
        print(f"年份自洽检查：{len(d.get('statutes', []))} 条法条 ｜ era_map {len(era_map)} 个年号")
        if errors:
            print(f"  ERROR {len(errors)}")
            for sid, msg in errors:
                print(f"  ❌ [{sid}] {msg}")
        else:
            print(f"  ERROR 0 —— 全部 era_year 换算与 year_ce 一致")
        print(f"  （INFO {len(infos)} 条，--verbose 可看）")
    return errors, infos


# ---------- 自测 ----------
_BAD_LIB = {
    "version": "test",
    "era_map": {"洪武": 1368, "弘治": 1488},
    "statutes": [
        # 正确
        {"id": "G1", "era_year": "洪武三年", "year_ce": 1370},
        # 手滑：洪武三年写成 1371
        {"id": "B1", "era_year": "洪武三年", "year_ce": 1371},
        # 复合年数：洪武二十六年 必须 = 1393，写成 1392 就是错
        {"id": "B2", "era_year": "洪武二十六年", "year_ce": 1392},
        # 「元」是元年
        {"id": "G2", "era_year": "弘治元年", "year_ce": 1488},
        # 一字段两量：场合表里某一处错
        {"id": "B3", "era_year": "洪武二十六年", "year_ce": 1393,
         "effective_by_occasion": {
             "常服": {"era": "洪武三年", "year_ce": 1370},
             "公服": {"era": "洪武二十六年", "year_ce": 1394},  # 错
         }},
    ],
}


def selfcheck():
    ok = True
    tmp = os.path.join(BASE_DIR, "_era_test.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_BAD_LIB, f, ensure_ascii=False)

    print("era_check 双向自测（正向必抓到 / 反向必不误报）")
    errs, infos = check_lib(tmp, quiet=True)
    ids = {e[0] for e in errs}

    c1 = "B1" in ids
    print(f"  正向1 手滑差1年（洪武三年→1371）被抓到 ..... {'✅' if c1 else '❌'}")
    ok = ok and c1

    c2 = "B2" in ids
    print(f"  正向2 复合年数（洪武二十六年→1392）被抓到 .. {'✅' if c2 else '❌'}")
    ok = ok and c2

    c3 = "B3" in ids
    print(f"  正向3 场合表里单处错（公服1394）被抓到 .... {'✅' if c3 else '❌'}")
    ok = ok and c3

    c4 = "G1" not in ids and "G2" not in ids
    print(f"  反向1 正确的条目不误报 .................... {'✅' if c4 else '❌'}")
    ok = ok and c4

    os.remove(tmp)

    # 反向2：真库跑一遍不许炸
    if os.path.exists(LIB):
        e2, _ = check_lib(LIB, quiet=True)
        c5 = True  # 只要不抛异常
        print(f"  反向2 真库可读（当前 {len(e2)} 个不一致）.. {'✅' if c5 else '❌'}")
        ok = ok and c5
    else:
        print("  反向2 真库不存在 ......................... ❌")
        ok = False

    print(f"\n  自测结果：{'✅ 全过' if ok else '❌ 有失败'}")
    return ok


def main():
    if "--selfcheck" in sys.argv:
        sys.exit(0 if selfcheck() else 2)
    errs, infos = check_lib()
    if "--verbose" in sys.argv:
        for sid, msg in infos:
            print(f"  ℹ️  [{sid}] {msg}")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
