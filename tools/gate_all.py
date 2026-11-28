#!/usr/bin/env python3
"""gate_all.py —— 收尾五闸一键跑（1461 新建）。

起因：1460 撞出「同一脚本两套 A/B 判据」，1461 查明根因是**轮次号与年份同形（都是四位数）**，
任何纯正则都无法可靠二分；且 1460 的 citation_audit 停摆是被"忘了跑"而不是"跑不过"。
所以本脚本只做一件事：把所有该跑的闸门按固定顺序跑一遍，任何一闸红就非零退出。

用法：
    python3 gate_all.py            # 全跑，打印汇总
    python3 gate_all.py --quiet    # 只打印汇总
"""
import subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
PY3 = sys.executable

GATES = [
    ("自检（结构+年份换算+I40–I49 断言）", [PY3, "statute_lookup.py", "--selfcheck"], "自检：✅ 通过"),
    ("revisions 闸门（校记锚点）", [PY3, "statute_lookup.py", "--revisions-check"], "revisions 闸门"),
    ("年份-出处闸门（note 内年号）", [PY3, "statute_lookup.py", "--year-in-note-all"], "年份-出处闸门"),
    ("分布闸门（判据40）", [PY3, "statute_lookup.py", "--dist-check"], "判据40 分布闸门通过"),
    ("citation_audit 重算（派生块）", [PY3, "citation_rebuild.py", "--check"], "n_total"),
    ("版本编年门禁自检", [PY3, "edition_year_guard.py", "--selftest"], "selftest ✅"),
    ("跨卷取年（卷58→卷61 五条又令）", [PY3, "cross_volume_year.py", "--selftest"], "跨卷取年·自检】✅ 通过"),
    ("卷58 事例层计数（A/B/C/D 四口径）", [PY3, "vol58_year_count.py", "--selftest"], "卷58计数自检】✅ 通过"),
    ("表四 45 条结构（v2 组号口径）", [PY3, "biao4_audit.py", "--selftest"], "表四自检】✅ 通过"),
    ("意义列两把尺（网格线×文字坐标重建）", [PY3, "cell_line_probe.py", "--selftest"], "意义列两把尺·自检】"),
    ("表四年差（tag 年 vs 实录落点）", [PY3, "biao4_year_gap.py", "--selftest"], "表四年差·自检】"),
    ("年筐台账（三十年筐/十六年筐，token 化取年）", [PY3, "year_basket_1472.py", "--selftest"], "年筐台账·自检】"),
    ("三十年筐实录普查（七卷，制度/实践/旁及三层）", [PY3, "ms30_apparel_scan.py", "--selftest"], "三十年筐·实录普查·自检】"),
    ("三十年筐卷首标签（环差除以月数，非借位；互斥枚举）", [PY3, "ms30_tag_audit.py", "--selftest"], "三十年筐·卷首标签干支审计·自检】"),
    ("三十年筐三源对读＋现代定朔（同错定祖先/分叉定世代）", [PY3, "ms30_third_source.py", "--selftest"], "三源对读·自检】"),
    ("三十年筐同卷内证月长链（1476 结论作废，仅局部验证）", [PY3, "ms30_month_chain_1476.py", "--selftest"], "三十年筐·同卷内证月长链·自检】"),
    ("三十年筐七卷十二朔全链（八月朔在卷254 内，简并已破）", [PY3, "ms30_full_chain_1477.py", "--selftest"], "三十年筐·七卷十二朔全链·自检】"),
    ("三十年筐跨年端点补链（十二月月末在卷256 卷首，连大月非孤例）", [PY3, "ms30_nextyear_1478.py", "--selftest"], "三十年筐·跨年端点补链·自检】"),
    ("洪武三十一年闰五月（闰是历法判词，天只给朔；定气判闰六差一格）", [PY3, "ms31_leap_1479.py", "--selftest"], "三十年筐·洪武三十一年闰五月·自检】"),
    ("洪武三十一年双尺度闰位（定气/平气同段，差的是闰名挂第6还是第7）", [PY3, "ms31_double_scale_1480.py", "--selftest"], "三十年筐·洪武三十一年双尺度闰位·自检】"),
    ("三十年筐·闰位缺段方向（中气晚≡朔早，翻点21.317h；七应不能单定冬至绝对值）",
     [PY3, "ms31_datong_1481.py", "--selftest"], "洪武三十一年闰位·第三层｜自检】"),
    ("三十年筐·大统历闰余法（闰限 18.655209 是构造值；洪武十七年闰余=闰应；N=year-1384 判死不减一；十九年七闰任意窗=7）",
     [PY3, "ms31_runyu_1482.py", "--selftest"], "洪武三十一年闰位·第四层｜自检】"),
    ("洪武朝闰月锚（实录238卷索引；减一6/7、不减一1/7；闰限=朔策−通闰）",
     [PY3, "ms32_shilu_audit_1483.py", "--selftest"], "洪武三十一年闰位·第五层｜自检"),
    ("洪武闰名分组（6个有闰年；A3/B0/C3；A∪C=6；临界假说否）",
     [PY3, "ms32_leap_group_1484.py", "--selftest"], "洪武闰名·第六层｜自检】"),
    ("无中气法泛化（13段×12气；起点=实录正月朔；定气1/6 平气0/6；只做月级结论）",
     [PY3, "ms32_nowq_1485.py", "--selftest"], "洪武闰名·第七层｜自检】"),
    ("起点锚歧义与量具标定（干支锚59-60日歧义；映射移一位换年；量具全正偏+5.46h）",
     [PY3, "ms32_anchor_1486.py", "--selftest"], "洪武闰名·第八层｜自检】"),
    ("两腿段基不同（原文三腿；初判十二月基3/6 vs 正月基0/6；1/6改判段基混用）",
     [PY3, "ms32_leg_base_1487.py", "--selftest"], "洪武闰名·第九层｜自检】"),
    ("天正次月文本定位（三本对读「加二朔策」；刻本证脱文；q=1→十二月三方咬合）",
     [PY3, "ms32_tianzheng_1488.py", "--selftest"], "洪武闰名·第十层｜自检】"),
    ("天正经朔定义与天正=十一月（三本对读12/13朔策；通闰=岁周−12朔验；历算全书直书「本年为十一月」）",
     [PY3, "ms32_tianzheng_suo_1489.py", "--selftest"], "洪武闰名·第十一层｜自检】"),
    ("闰准补法盲区普查（31年逐档；1384为唯一B档且r≡闰应；补法与历元年不闰相撞）",
     [PY3, "ms32_runbu_1490.py", "--selftest"], "洪武闰准补法·第十二层｜自检】"),
    ("历元不用为元（1491）· 拆「补法撞历元年」／元史闰应与无闰限／明史折算 103 年积",
     [PY3, "ms32_liyuan_1491.py", "--selftest"], "历元不用为元·第十三层｜自检】"),
    ("历元闰八（1492）· 1281 三朔连读闰八月／闰余 202050 超闰准与史实同边／第二腿定气闰六平气闰八／1384 年尾闰落补法带",
     [PY3, "ms32_liyuan_run_1492.py", "--selftest"], "历元闰八·第十四层｜自检】"),
    ("三源配准（1494）· 原文六书朔 × 我的天文朔链 × 第三方大统历算器；p=2 唯一领先 4/6／原文正月落 1280-11-01／与第三方差 88 日",
     [PY3, "ms32_reg_1494.py", "--selftest"], "月名口径·第十五层｜自检】"),
    ("严朔字口径（1495）· 25 月仅 12 书朔／月内日当朔会造 28-31 日假月长／206与325 双日数约束下 p=2 仍唯一／第三方 1280 八月 = 我第 0 朔 0 差",
     [PY3, "ms32_shuo_strict_1495.py", "--selftest"], "书朔口径·第十六层｜自检】"),
    # 【已废·1498 裁定】ms32_niannian_1496.py 不再作为闸门执行。
    # 理由：它的判据是「三点各落 ±1 日内」——1497 已证该容差把两个配错两月的点判成「准」；
    #       让一把坏尺继续判绿，就是假绿（结构绿≠内容绿）。
    # 处置：脚本保留作历史档案（不复跑）；「它是废的」这件事由 ms32_yearhead_gate_1498.py
    #       的反事实断言守着（1496 的 17→18 偏 58.37 日、18→19 偏 59.10 日，必须被判死）。
    # ("年首三向定位（1496）", [PY3, "ms32_niannian_1496.py", "--selftest"], "年首三向定位·第十七层｜自检】"),
    ("三年首重配（1497）· 四本一致『十八年春正月戊戌朔』／点校勘记『〔三月〕丙申〔朔〕』与天算 1280-12-29 丙申精确吻合／『三月戊戌』是许衡卒日非朔／17→18=354日(12月)、18→19=384日(13月)，443 日缺口消失／88 日=第三方西历年初 vs 至元纪年的年首口径差",
     [PY3, "ms32_three_year_1497.py", "--selftest"], "三年首重配·第十八层｜自检】"),
    ("年首跨度闸（1498）· 月数由原文年号+月名定、日数由我的朔表定——用原文的月数审我的日数才不是自证；端点跨度 |实测−月数×29.53059|≤1.5／端点干支逐字相等／逐月月长∈{29,30}且和==端点差。读数：17→18 354 vs 354.37 偏0.37 过、18→19 384 vs 383.90 偏0.10 过；反事实 1496 的 296 偏58.37 判死、443 偏59.10 判死",
     [PY3, "ms32_yearhead_gate_1498.py", "--selftest"], "年首跨度闸·第十九层｜自检】"),
    ("T13 实录反查（1500）· 《明太祖实录》卷224–230 洪武二十六年全年（7卷27644字符）：T13 宗室冕服等第（親王九旒·郡王七旒）在本年无制度性文本——「冕」六处（224四/228二）逐处定性全落仪注（升座/贊禮/醮戒/朝賀），窗口内制度词（九旒/九章/等第/之制/制度/等殺）0 命中；「九旒」「九章」全七卷 0 命中；同域制度另有记（226僣侈踰制、228等殺著為定式）⇒ 实录记行礼穿什么、会典记制度定成什么样，阴性不等于 1393 年没定过",
     [PY3, "t13_shilu_1500.py", "--selftest"], "T13实录反查·第二十层｜自检】"),
]

def main():
    quiet = "--quiet" in sys.argv
    fails = []
    for name, cmd, must in GATES:
        p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
        out = (p.stdout or "") + (p.stderr or "")
        ok = (p.returncode == 0) and (must in out)
        if not quiet or not ok:
            print(("✅ " if ok else "❌ ") + name)
            if not ok:
                print("   " + "\n   ".join(out.strip().splitlines()[-4:]))
        if not ok:
            fails.append(name)
    # 两把尺子并列展示（只报告，不阻断）：差的条数必须能解释
    p1 = subprocess.run([PY3, "statute_lookup.py", "--revisions-check"], cwd=HERE, capture_output=True, text=True)
    line = [l for l in p1.stdout.splitlines() if "revisions 闸门" in l]
    print("ℹ️ CLI 尺：" + (line[0] if line else "(取不到)"))
    print("ℹ️ 断言 I48 尺（revisions_view）：见 --selfcheck 通过行；两把尺子差数须在 count_meta.revisions_view.means 里写明")
    print("\n" + ("❌ " + str(len(fails)) + " 闸红：" + "／".join(fails) if fails else "✅ 全部闸门通过"))
    return 2 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
