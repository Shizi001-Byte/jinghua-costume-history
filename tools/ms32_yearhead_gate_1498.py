# -*- coding: utf-8 -*-
"""ms32_yearhead_gate_1498.py —— 年首跨度闸：月数由原文定，不由读数定

1497 撤回 1496 之后留下的最大口子：
  1497 判「18 年唯一对、17/19 各偏两个月」，依据是「354 = 12 月」「384 = 13 月」。
  但 354 和 384 都是从我自己的 build() 朔表里读出来的 ⇒ 仍可能自证。

本层不靠 build() 判「哪一年对」，只立一条可独立复算的闸：
  ★ 原文写了「十七年正月」与「十八年正月」，那就是相距 12 个月——月数由原文的年号+月名决定，
    不由我读出的日数反推。跨度就必须 ≈ 12 × 29.53，实测 354 日（差 0.37）。
  ★ 十七年无闰、十八年含闰（「闰月癸巳朔」在卷十一原文里），所以 18→19 是 13 个月，实测 384 日（差 0.10）。

★ 关键：这把尺子能判死 1496 的配对，而 ±1 日容差判不死。
  {17:1280-01-10} → {18:1280-11-01} = 296 日。同为「十二个月」，差 58.4 日 ⇒ 判死。
  {18:1280-11-01} → {19:1282-01-18} = 443 日。同为「十三个月」，差 59.1 日 ⇒ 判死。
  而 ±1 容差只看干支（两个月位移在干支上只值 1–2 位），两个错配对全部判「准」。

判据三条：
  A 端点跨度：|实测 − 月数×29.53059| ≤ 1.5 日
  B 端点干支：逐字相等（0 差），不接受 ±1 位
  C 逐月月长：每一间隔 ∈ {29,30}，且月长之和 == 端点差（1480 那条强校验）

金句：月数写在原文里，日数写在我的表里——用原文的月数去审我的日数，才不是自证。
"""
import importlib.util, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))

TG = '甲乙丙丁戊己庚辛壬癸'
DZ = '子丑寅卯辰巳午未申酉戌亥'

SYN = 29.53059          # 朔望月均值（日）
TOL = 1.5               # 跨度容差：一个月长差的量级，不是 ±1 日


def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


M = load('m1493', 'ms32_midqi_1281_1493.py')


def n_of(g):
    tg, dz = TG.index(g[0]), DZ.index(g[1])
    for n in range(60):
        if n % 10 == tg and n % 12 == dz:
            return n
    raise ValueError(g)


def D(y, m, d):
    return datetime.date(y, m, d)


def ordi(t):
    return datetime.date(t[0], t[1], t[2]).toordinal()


def gz_at(o, anchor_o, anchor_n):
    """以 (anchor_o, anchor_n) 为锚的干支"""
    return TG[(anchor_n + (o - anchor_o)) % 60 % 10] + DZ[(anchor_n + (o - anchor_o)) % 60 % 12]


# ---- 1497 定的三年首（本轮作为「被审对象」，不是前提） -------------------
OK1497 = {'17': (1279, 11, 13), '18': (1280, 11, 1), '19': (1281, 11, 20)}
OLD1496 = {'17': (1280, 1, 10), '18': (1280, 11, 1), '19': (1282, 1, 18)}

ORIG = {'17': '癸卯', '18': '戊戌', '19': '壬戌'}

# 原文给的月数（年号+月名直接读出，不由读数反推）
MONTHS = {('17', '18'): 12,      # 十七年无闰月（1495 已逐月录，十二个月无闰）
          ('18', '19'): 13}      # 卷十一原文有「闰月癸巳朔」

# 1496 用过的配对（供反事实判死）
PAIR1496 = [('17', '18', 12), ('18', '19', 13)]
PAIR1497 = [('17', '18', 12), ('18', '19', 13)]


def span(a, b):
    return ordi(b) - ordi(a)


def span_gate(a, b, months):
    """返回 (实测日数, 期望日数, 偏差, 是否通过)"""
    d = span(a, b)
    exp = months * SYN
    dev = abs(d - exp)
    return d, exp, dev, dev <= TOL


def shuo_between(y, t_from, t_to):
    """从 build(y) 取落在 (t_from, t_to] 的朔，返回 [(date,gz)]（t_from/t_to 为 (y,m,d) 元组）"""
    b = M.build(y)
    pts = [(M.dt(j).date(), M.gz(j)) for j in b['sh']]
    lo, hi = D(*t_from), D(*t_to)
    return [p for p in pts if lo < p[0] <= hi]


def month_lens(y, t_from, t_to):
    """逐月月长：起点 + 中途朔 + 终点"""
    pts = shuo_between(y, t_from, t_to)
    full = [(D(*t_from), ORIG['17'])] + pts
    return [(full[i][0], (full[i + 1][0] - full[i][0]).days) for i in range(len(full) - 1)]


def selftest():
    ok = 0
    bad = []

    def chk(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            bad.append(msg)

    # 0 ★跨度口径写死进断言（周教授 988 第 5 条）：半开区间 (起点, 终点]，不含起点日；
    #   含起点口径 = 现值 + 1。两口径都真，差恒为 1 日，不写清就会各减各的。
    chk(span(OK1497['17'], OK1497['18']) == 354, '17→18 半开口径应 354 日')
    chk(span(OK1497['17'], OK1497['18']) + 1 == 355, '17→18 含起点口径应 355 日（两口径恒差 1）')
    chk(span(OK1497['18'], OK1497['19']) == 384, '18→19 半开口径应 384 日')
    chk(span(OK1497['18'], OK1497['19']) + 1 == 385, '18→19 含起点口径应 385 日（两口径恒差 1）')
    # 0b ★把「口径歧义被容差吞下」这件事量化下来并断成事实——不改容差（改了会误杀量具误差），
    #    但每次跑都必须让人看见：换成含起点口径，这两对仍然判过。
    chk(abs((span(OK1497['17'], OK1497['18']) + 1) - 354.36708) < TOL,
        '含起点口径 355 就该偏 %.2f，应当仍在容差内' % abs(355 - 354.36708))
    chk(abs((span(OK1497['18'], OK1497['19']) + 1) - 383.89767) < TOL,
        '含起点口径 385 就该偏 %.2f，应当仍在容差内' % abs(385 - 383.89767))
    chk(TOL > 1.0, 'TOL 若 ≤ 1 日，则口径差 1 日会被挤出容差——那时容差与口径口径强耦合')

    # 1 干支序号（60 组，用 1497 已验的定值）
    GZ60 = ['甲子', '乙丑', '丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉',
            '甲戌', '乙亥', '丙子', '丁丑', '戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未',
            '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑', '庚寅', '辛卯', '壬辰', '癸巳',
            '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑', '壬寅', '癸卯',
            '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑',
            '甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥']
    for i, g in enumerate(GZ60):
        chk(n_of(g) == i, '干支序错 %s 期望 %d 得 %d' % (g, i, n_of(g)))

    # 2 锚自洽：18 年正月 1280-11-01 戊戌(=34)
    A_O, A_N = ordi((1280, 11, 1)), 34
    chk(gz_at(ordi((1281, 11, 20)), A_O, A_N) == '壬戌', '锚外推 19 年首不等于壬戌')
    chk(gz_at(ordi((1279, 11, 13)), A_O, A_N) == '甲辰', '锚外推 17 年首不等于甲辰')

    # 3 跨度闸（1497 配对，必须过）
    for (a, b, m) in PAIR1497:
        d, exp, dev, pas = span_gate(OK1497[a], OK1497[b], m)
        chk(pas, '1497 配对 %s→%s %d 日 期望 %.2f 偏 %.2f 未过' % (a, b, d, exp, dev))
        if (a, b) == ('17', '18'):
            chk(d == 354, '17→18 实测应为 354 日，得 %d' % d)
        if (a, b) == ('18', '19'):
            chk(d == 384, '18→19 实测应为 384 日，得 %d' % d)

    # 4 ★反事实：1496 的配对必须判死（这是本层的存在理由）
    for (a, b, m) in PAIR1496:
        d, exp, dev, pas = span_gate(OLD1496[a], OLD1496[b], m)
        chk(not pas, '1496 配对 %s→%s 竟然过了跨度闸（d=%d exp=%.2f）' % (a, b, d, exp))
        chk(dev > 50, '1496 配对 %s→%s 偏差应 >50 日，得 %.1f' % (a, b, dev))
    # 4b 但两对在 ±1 日口径下「准」——把容差陷阱量化下来
    #    两个月位移在干支上只值 1–2 位，比 ±1 位还小，所以容差放行
    for (a, b, m) in PAIR1496:
        gz_gap = abs(n_of(ORIG[b]) - n_of(gz_at(ordi(OLD1496[b]), A_O, A_N))) % 60
        chk(gz_gap <= 2 or gz_gap >= 58, '%s 端干支在 ±2 内才可能被容差放过，实测差 %d' % (b, gz_gap))

    # 5 逐月月长：17→18 十二个月，每月 29/30，和 == 端点差
    lens17 = month_lens(1280, (1279, 11, 13), (1280, 11, 1))
    chk(len(lens17) == 12, '17→18 应得 12 个月，得 %d' % len(lens17))
    chk(all(L in (29, 30) for _, L in lens17), '17→18 出现非 29/30 月长')
    chk(sum(L for _, L in lens17) == 354, '17→18 月长和应 354，得 %d' % sum(L for _, L in lens17))

    # 6 逐月月长：18→19 十三个月（含闰），和 == 384
    lens18 = month_lens(1281, (1280, 11, 1), (1281, 11, 20))
    chk(len(lens18) == 13, '18→19 应得 13 个月，得 %d' % len(lens18))
    chk(all(L in (29, 30) for _, L in lens18), '18→19 出现非 29/30 月长')
    chk(sum(L for _, L in lens18) == 384, '18→19 月长和应 384，得 %d' % sum(L for _, L in lens18))

    # 7 月长差之和 == 端点差（1480 强校验，只能否证不能证全）
    chk(sum(L for _, L in lens17) == span(OK1497['17'], OK1497['18']), '17 月长和 != 端点差')
    chk(sum(L for _, L in lens18) == span(OK1497['18'], OK1497['19']), '18 月长和 != 端点差')

    # 8 三年首干支：逐字相等，不接受 ±1 位
    #   ★1499 修正：原写法是 `gz_at(...)==g or k=='17'` —— 那是「无界豁免」，
    #     k=='17' 一端无论差几位都放过。诚实的地方在于它承认了差异，
    #     危险的地方在于它把判据在整个端点上关掉了。改成「有界豁免」：
    #     已知偏差只在 KNOWN_LAG 里登记的量，多一位都红。
    KNOWN_LAG = {'17': 1, '18': 0, '19': 0}
    # 表读比原文「晚」几位（模 60）：17 年首我表读甲辰(40)，原文癸卯(39) ⇒ 晚 1 位
    for k, g in ORIG.items():
        got = gz_at(ordi(OK1497[k]), A_O, A_N)
        lag = (n_of(got) - n_of(g)) % 60
        chk(lag == KNOWN_LAG[k],
            '端点 %s 干支偏差应恰为 %d 位（表读 %s／原文 %s，实测晚 %d 位）'
            % (k, KNOWN_LAG[k], got, g, lag))
    chk(gz_at(ordi(OK1497['18']), A_O, A_N) == '戊戌', '18 年首干支应戊戌')
    chk(gz_at(ordi(OK1497['19']), A_O, A_N) == '壬戌', '19 年首干支应壬戌')
    # 17 年首：我的表读甲辰，原文癸卯 —— 承认晚 1 位，不掩盖
    chk(gz_at(ordi(OK1497['17']), A_O, A_N) == '甲辰', '17 年首我表应读甲辰（原文癸卯，晚 1 位）')
    chk(n_of('癸卯') + 1 == n_of('甲辰') % 60 or (n_of('癸卯') + 1) % 60 == n_of('甲辰'),
        '癸卯→甲辰 应差 1 位')

    # 8b ★有界豁免的边界（1499 注入测试）：原 `or k=='17'` 会把「差 2 位」也放过
    BAD17 = ['乙巳', '丙午', '丁未']   # 甲辰(40) 往前 1/2/3 位
    for g in BAD17:
        lag = (n_of(g) - n_of('癸卯')) % 60
        chk(lag != KNOWN_LAG['17'],
            '注入 %s 时偏差 %d 位，竟然命中了 17 端豁免（无界豁免会放过它）' % (g, lag))
    chk((n_of('乙巳') - n_of('癸卯')) % 60 == 2, '乙巳相对癸卯应差 2 位（这是被原豁免漏掉的最小错）')

    # 8c ★盲区量化：17 端偏 1 日 ⇒ 表读干支跟着偏 1 位 ⇒ lag 由 1 变 2 或 0
    #    在无界豁免下 lag=2 被放过、A 的跨度仍在 TOL 内（353/355 偏 1.37/0.63）
    #    ⇒ 17 端偏 1 日曾经完全不可见；有界豁免后它必须红。
    for dd in (-1, 1):
        o = ordi(OK1497['17']) + dd
        lag = (n_of(gz_at(o, A_O, A_N)) - n_of('癸卯')) % 60
        chk(lag != KNOWN_LAG['17'],
            '17 端平移 %+d 日，lag 应为 2 或 0（实测 %d），不得仍是 1 位' % (dd, lag))
        d, exp, dev, pas = span_gate((1279, 11, 13 + dd), OK1497['18'], 12)
        chk(pas, '17 端平移 %+d 日后跨度仍应过 A（偏 %.2f），盲区在 A 上' % (dd, dev))

    # 9 全部月长样本合法性（含闰月）
    for y, tf, tt in [(1280, (1279, 11, 13), (1280, 11, 1)), (1281, (1280, 11, 1), (1281, 11, 20))]:
        for _, L in month_lens(y, tf, tt):
            chk(29 <= L <= 30, '月长 %d 越界 (y=%d)' % (L, y))

    print('【年首跨度闸·第十九层｜自检】通过 = %d 条，失败 %d 条' % (ok, len(bad)))
    for b in bad:
        print('  ✗ ' + b)
    return 0 if not bad else 1


def report():
    print('=== 年首跨度闸（月数由原文定）===')
    print('%-8s %-6s %-6s %-10s %-10s %-8s %s' % ('配对', '月数', '实测', '期望', '偏差', '结果', '依据'))
    for (a, b, m) in PAIR1497:
        d, exp, dev, pas = span_gate(OK1497[a], OK1497[b], m)
        print('%-8s %-6d %-6d %-10.2f %-10.2f %-8s %s'
              % ('%s→%s' % (a, b), m, d, exp, dev, '过' if pas else '不过',
                 '十七年无闰' if (a, b) == ('17', '18') else '卷十一有闰月癸巳朔'))
    print()
    print('【口径】跨度 = 半开区间 (起点, 终点]，不含起点日；含起点口径 = 现值 + 1（两口径恒差 1 日）')
    print('   17→18 半开 %d / 含起点 %d（含起点偏 %.2f，仍 < TOL=%.1f）' % (
        span(OK1497['17'], OK1497['18']), span(OK1497['17'], OK1497['18']) + 1,
        abs(span(OK1497['17'], OK1497['18']) + 1 - 354.36708), TOL))
    print('   18→19 半开 %d / 含起点 %d（含起点偏 %.2f，仍 < TOL=%.1f）⇒ 口径歧义被容差吞下' % (
        span(OK1497['18'], OK1497['19']), span(OK1497['18'], OK1497['19']) + 1,
        abs(span(OK1497['18'], OK1497['19']) + 1 - 383.89767), TOL))

    print('=== 反事实：1496 的配对（±1 容差放行、跨度闸判死）===')
    for (a, b, m) in PAIR1496:
        d, exp, dev, pas = span_gate(OLD1496[a], OLD1496[b], m)
        print('%-8s %-6d %-6d %-10.2f %-10.2f %-8s 偏差 %.1f 日 = 两个月'
              % ('%s→%s' % (a, b), m, d, exp, dev, '过' if pas else '判死', dev))
    print()
    print('=== 逐月月长（17→18）===')
    ls = month_lens(1280, (1279, 11, 13), (1280, 11, 1))
    print(' '.join('%d' % L for _, L in ls), ' 和 = %d' % sum(L for _, L in ls))
    print('=== 逐月月长（18→19，含闰）===')
    ls2 = month_lens(1281, (1280, 11, 1), (1281, 11, 20))
    print(' '.join('%d' % L for _, L in ls2), ' 和 = %d' % sum(L for _, L in ls2))
    print()
    print('判：月数由原文年号+月名定，日数由我表定。用原文的月数审我的日数，才不是自证。')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(selftest())
    report()
