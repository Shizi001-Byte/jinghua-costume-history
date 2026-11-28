# -*- coding: utf-8 -*-
"""T13 实录反查（1500 轮）——宗室冕服等第（亲王九旒·郡王七旒）

T13 本体（读库确认，不凭记忆）：
  title = 宗室冕服等第（亲王九旒·郡王七旒）
  era_year = 洪武二十六年（1393）／year_source = book／attribution.level = secondary_only
  attribution.note 旧话 = 「未取得洪武/永乐朝《实录》原始诏令一手，维持 secondary_only、不越级」

本脚本只做一件事：把「未查实录」改成「查过了，是这样」。
读本地《明太祖实录》卷 224–230（洪武二十六年全年，7 卷），判：
 1) 「冕」字确有出现（224 四处、228 两处）——不许说「实录没提冕服」
 2) 这六处全部落在**仪注场景**（婚礼醮戒／朝贺升座／东宫受贺），窗口内含仪注标志词（升座/贊禮/醮戒/儀注/朝賀/受冊/迎）
 3) 没有一处落在**制度语境**（九旒/九章/等第/之制/制度/等殺）
 4) 「九旒」「九章」七卷零命中；「冠服」只三处且都不是宗室冕服制度（224 婚礼、229 儒学訓導）

结论不是「实录缺一条」，而是「实录本年记的是行礼时穿什么（仪注），会典记的是制度定成什么样（令/文册）」。
配合 1465 温少华判据（正德《会典》『某某年定』＝采编自文册的**制度制定时间**），
「实录本年无制度文本」不等于「1393 年没有定过」，也不足以升级 T13 的 level。

判据：T13实录反查·第二十层｜自检】通过
"""
import io
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SL = os.path.join(BASE, 'lib', 'raw_volume', 'ms30', 'sl')

FILES = [224, 225, 226, 227, 228, 229, 230]

# 仪注标志词：出现即说明这段在讲「行礼时穿什么」
RITE = ['升座', '贊禮', '醮戒', '儀注', '朝賀', '受冊', '親迎', '廟見', '受醮']
# 制度标志词：出现即说明这段在讲「定成什么样」
INST = ['九旒', '九章', '等第', '之制', '制度', '等殺']

# 登记命中位置（不许删，删了就是把尺子改到只剩自己要的读数）
KNOWN = [
    (224, '王服袞冕', '親王婚礼醮戒，王服袞冕行礼'),
    (228, '東宮具冕服', '東宮受賀升座，具冕服行礼'),
]

WIN = 160  # 上下文窗口半径


def load():
    out = {}
    for v in FILES:
        p = os.path.join(SL, '%03d.txt' % v)
        with io.open(p, encoding='utf-8', errors='ignore') as h:
            out[v] = h.read()
    return out


def windows(t, ch='冕'):
    """返回所有含 ch 的上下文窗口（以每次出现为中心）"""
    res = []
    for v in FILES:
        s = t[v]
        i = -1
        while True:
            i = s.find(ch, i + 1)
            if i < 0:
                break
            res.append((v, s[max(0, i - WIN):i + WIN], i))
    return res


def selftest():
    ok, bad = 0, []

    def chk(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            bad.append(msg)

    t = load()

    # 1. 七卷齐、年号锚、年首到年末
    chk(len(t) == 7, '卷数不足 %d' % len(t))
    for v in FILES:
        chk('洪武二十六年' in t[v], '卷%d 无洪武二十六年年号锚' % v)
    chk('正月' in t[224], '卷224 无正月')
    chk('十二月' in t[230], '卷230 无十二月')

    # 2. 「冕」确有出现——这六处是事实，不许说成零
    ws = windows(t)
    chk(len(ws) == 6, '「冕」窗口应为 6 处（224 四 + 228 二），实得 %d' % len(ws))
    chk(sum(1 for v, _, _ in ws if v == 224) == 4, '卷224「冕」应 4 处')
    chk(sum(1 for v, _, _ in ws if v == 228) == 2, '卷228「冕」应 2 处')
    for v in (225, 226, 227, 229, 230):
        chk(t[v].count('冕') == 0, '卷%d 意外出现「冕」' % v)

    # 3. 每一处都必须是仪注场景（至少一个仪注标志词）
    for v, w, _ in ws:
        chk(any(k in w for k in RITE), '卷%d 冕窗口无仪注标志词：%s' % (v, w[:60]))

    # 4. 每一处都不得落在制度语境
    for v, w, _ in ws:
        for k in INST:
            chk(k not in w, '卷%d 冕窗口出现制度词「%s」：%s' % (v, k, w[:60]))

    # 5. 登记命中必须逐字在
    for v, s, why in KNOWN:
        chk(s in t[v], '登记命中缺失：卷%d「%s」（%s）' % (v, s, why))

    # 6. 「九旒」「九章」七卷零命中——T13 的核心形制词不在本年纪录
    for k in ('九旒', '九章'):
        hit = [v for v in FILES if k in t[v]]
        chk(not hit, '「%s」在卷 %s 命中，T13 反查需重判' % (k, hit))

    # 7. 「冠服」三处都不是宗室冕服制度
    for v in FILES:
        n = t[v].count('冠服')
        if n:
            chk(v in (224, 229), '卷%d 出现「冠服」，未登记' % v)
    chk(t[229].count('冠服') == 1 and '訓導' in t[229], '卷229「冠服」应为儒学訓導，不是宗室')
    chk(t[224].count('冠服') == 2, '卷224「冠服」应 2 处（婚礼仪注）')

    # 8. 同域制度确有记载（本年不是空白年）：公侯服舍器用等杀、功臣僣侈
    chk('等殺著為定式' in t[228], '卷228 缺「等殺著為定式」——本年制度记载锚')
    chk('僣侈踰制' in t[226], '卷226 缺「僣侈踰制」')

    print('【T13实录反查·第二十层｜自检】通过 = %d 条，失败 %d 条' % (ok, len(bad)))
    for b in bad:
        print('   ✗', b)
    return not bad


def report():
    t = load()
    ws = windows(t)
    print('T13 = 宗室冕服等第（親王九旒·郡王七旒）／洪武二十六年(1393)／book／secondary_only')
    print('查《明太祖实录》卷 224–230（洪武二十六年全年）：%d 卷 / %d 字符' %
          (len(t), sum(len(x) for x in t.values())))
    print('「冕」六处，逐处定性：')
    for v, w, i in ws:
        rite = [k for k in RITE if k in w]
        print('   卷%-3d 仪注标志=%-8s …%s…' % (v, '/'.join(rite[:2]), w[60:150].replace('\n', '')))
    print('制度词（九旒/九章/等第/之制/制度/等殺）在六处冕窗口内：0 命中')
    print('全七卷「九旒」「九章」：0 命中；「冠服」3 处（224 婚礼 2、229 儒学訓導 1）')
    print('同域制度记载（同一年、不同事）：226 服舍器用僣侈踰制／228 公侯服舍器用等殺著為定式')
    print('结论：实录本年记的是「行礼时穿什么」，会典记的是「制度定成什么样」；')
    print('      本届无制度性冕服文本，不等于 1393 年没定过（1465：会典「某某年定」＝文册采编的制度制定时间）。')
    print('      T13 维持 secondary_only；账由「未查实录」改为「已查本年七卷，阴性有解释」。')


if __name__ == '__main__':
    import sys
    if '--selftest' in sys.argv:
        sys.exit(0 if selftest() else 1)
    else:
        report()
