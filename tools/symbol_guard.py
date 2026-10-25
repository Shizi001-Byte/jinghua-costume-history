#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
symbol_guard.py — 模块级符号覆盖检查器

为什么存在：
  2026-10-24 第1042次唤醒，我给 statute_lookup.py 加「按场合查带」时，
  在模块级又写了一个 CN_NUM = {"一":1,...,"九":9}。
  文件第49行早就有一个 CN_NUM（含「十」「二十」「二十六」）——被我覆盖了。
  后果：所有年号解析静默失效，四向验证四条全是「无法解析年份」。
  而 --selfcheck 全程 ✅ 绿，因为它不测 --year。

  那一类 bug 的特征是：
    - 不报错
    - 跑得通
    - 输出的是别的事
    - 而且只在「恰好跑到那条路径」时才暴露

  判据 24：加新代码时，最容易弄坏的不是新代码，是同名的旧东西。
  判据 25：回归断言该写「我真的错过的地方」，不该写「我想象可能错的地方」。

检查三类静默覆盖（都在模块级）：
  1. dup_assign  同一文件里同一个名字被赋值两次   → 后一个静默覆盖前一个
  2. dup_def     同一文件里同一个 def/class 定义两次 → 后一个静默覆盖前一个
  3. shadow_builtin  模块级常量名撞 Python 内建   → 想用 list() 时拿到一个列表

被排除、不报警的（都是有意写法）：
  - 函数/类内部的局部变量（只看 module.body 顶层）
  - __name__ == '__main__' 块内的赋值
  - try/except、if/else 不同分支里的同名赋值（按 info 报，不计错误）

用法：
  python3 symbol_guard.py                 # 扫当前目录及子目录所有 .py
  python3 symbol_guard.py --file X.py     # 只查一个文件
  python3 symbol_guard.py --selfcheck     # 内置 fixture 双向自测
  python3 symbol_guard.py --quiet         # 只报错误不报 info

退出码：
  0 = 干净（无 ERROR 级覆盖）
  1 = 发现 ERROR 级覆盖
  2 = 检查器自身异常（自测失败等）
"""

import argparse
import ast
import builtins
import glob
import os
import sys

# 显式忽略的目录（快照与备份里是历史副本，查它们会淹没真问题）
SKIP_DIRS = {"snapshots", "__pycache__", ".git", "_去重归档", "logs", "backups"}

# 内建名 —— 模块级用这些名字会被检查器标出来
BUILTIN_NAMES = set(dir(builtins))

# 模块级常量的典型值类型（用于判断「这一条是不是常量定义」）
CONST_VALUE_NODES = (ast.Dict, ast.List, ast.Tuple, ast.Set,
                     ast.Constant, ast.JoinedStr)


def _branch_context(module_body, node):
    """返回 node 在 module.body 里所处的「分支容器」描述。

    Module 直挂 → ("top", None)
    Try 的 body/orelse/finalbody/handlers → ("try", 分支名)
    If 的 body/orelse → ("if", 分支名)
    其它（With/For/While）→ ("other", 类型名)
    """
    for top in module_body:
        if top is node:
            return "top", None
        for field, value in ast.iter_fields(top):
            if not isinstance(value, list):
                continue
            for item in value:
                # 只比一层容器，够用：把顶层容器当分支
                if item is node:
                    if isinstance(top, ast.Try):
                        if value is top.handlers:
                            return "try", "handlers"
                        return "try", field
                    if isinstance(top, ast.If):
                        return "if", field
                    return "other", type(top).__name__
    return "unknown", None


def scan_file(path, quiet=False):
    """扫描一个文件，返回 (errors, infos)。"""
    errors, infos = [], []
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
    except (SyntaxError, UnicodeDecodeError) as exc:
        infos.append((path, "parse", 0, f"无法解析，已跳过：{exc}"))
        return errors, infos

    # 收集模块级（含 try/if 容器内一层）的所有赋值与定义
    assigns = {}   # name -> [(lineno, branch_kind, branch_name, is_const)]
    defs = {}      # name -> [(lineno, kind)]

    def record_assign(name, lineno, branch_kind, branch_name, is_const):
        assigns.setdefault(name, []).append((lineno, branch_kind, branch_name, is_const))

    def walk_top(node_list, branch_kind, branch_name):
        for node in node_list:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        is_const = isinstance(node.value, CONST_VALUE_NODES)
                        record_assign(t.id, node.lineno, branch_kind, branch_name, is_const)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if isinstance(node.value, CONST_VALUE_NODES):
                    record_assign(node.target.id, node.lineno, branch_kind, branch_name, True)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs.setdefault(node.name, []).append(
                    (node.lineno, "class" if isinstance(node, ast.ClassDef) else "def"))
            elif isinstance(node, ast.If):
                # __name__ == '__main__' 块整体忽略
                test = node.test
                is_main_guard = False
                if isinstance(test, ast.Compare):
                    try:
                        left = ast.unparse(test.left)
                        if left == "__name__":
                            is_main_guard = True
                    except Exception:
                        pass
                if is_main_guard:
                    continue
                walk_top(node.body, "if", "body")
                walk_top(node.orelse, "if", "orelse")
            elif isinstance(node, ast.Try):
                walk_top(node.body, "try", "body")
                for h in node.handlers:
                    walk_top(h.body, "try", "handlers")
                walk_top(node.orelse, "try", "orelse")
                walk_top(node.finalbody, "try", "finalbody")
            elif isinstance(node, (ast.With, ast.For, ast.While)):
                # 这些容器的 body 里通常是有意处理，只收函数/类定义
                for field, value in ast.iter_fields(node):
                    if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
                        walk_top(value, "other", type(node).__name__)

    walk_top(tree.body, "top", None)

    # ---- 1. dup_assign ----
    for name, sites in assigns.items():
        if len(sites) < 2:
            continue
        branches = {(k, v) for _, k, v, _ in sites}
        # 都在不同分支里 → 可能是有意的 fallback，降为 info
        top_level = [s for s in sites if s[1] == "top"]
        const_sites = [s for s in sites if s[3]]
        lines = [s[0] for s in sites]
        if len(top_level) >= 2:
            # 两处以上都在模块顶层 → 纯静默覆盖，几乎总是 bug。
            # 2026-10-24 第1042次那个 CN_NUM 就是这种形态。
            errors.append((path, "dup_assign", lines[0],
                           f"模块级常量 `{name}` 被重复赋值 {len(sites)} 次，行 {lines}"
                           f" —— 后一处会静默覆盖前一处"))
        else:
            # 顶层一处 + 分支内一处 → 典型是「默认值 + 失败回退」
            # （例：LOCAL_MODEL_ENABLED = True / except: = False）。
            # 这是有意写法，绝不能报 ERROR —— 检查器误报比漏报更糟，
            # 它会把人推去改一个本来正确的东西。只提醒看一眼。
            infos.append((path, "dup_assign_branch", lines[0],
                          f"`{name}` 顶层定义一次、分支内再定义一次，行 {lines}"
                          f"（分支名 {sorted(branches)}）—— 多为「默认值+回退」，请自行确认"))

    # ---- 2. dup_def ----
    for name, sites in defs.items():
        if len(sites) < 2:
            continue
        lines = [s[0] for s in sites]
        kinds = {s[1] for s in sites}
        errors.append((path, "dup_def", lines[0],
                       f"模块级 {sorted(kinds)} `{name}` 被定义 {len(sites)} 次，行 {lines}"
                       f" —— Python 不会重载，后一个会静默替换前一个"))

    # ---- 3. shadow_builtin ----
    # ⚠️ 注意：这里绝不能套 `if not quiet:`。
    # 2026-10-24 第1043次：第一版就是这么写的，结果 quiet=True 时这条检查整个被跳过，
    # 于是 --selfcheck 里「撞内建名」永远抓不到——工具会带着一个假功能上线。
    # quiet 只能控制「打印不打印」，不能控制「查不查」。
    for name, sites in assigns.items():
        if name in BUILTIN_NAMES and len(sites) == 1:
            # 只报模块级的（top）
            if sites[0][1] == "top":
                infos.append((path, "shadow_builtin", sites[0][0],
                              f"模块级常量 `{name}` 与 Python 内建同名"
                              f" —— 本文件内再用 `{name}()` 会报 'not callable'"))

    return errors, infos


def collect_files(root="."):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fn in filenames:
            if fn.endswith('.py'):
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


# ---------------------------------------------------------------- 自测

_FIXTURE_BAD = '''
CN_NUM = {"一": 1, "十": 10, "二十": 20, "二十六": 26}
OTHER = "ok"

def helper(x):
    return x

CN_NUM = {"一": 1, "九": 9}          # ← 覆盖，必须抓到

def helper(x):                        # ← 覆盖，必须抓到
    return x * 2

list = [1, 2, 3]                      # ← 撞内建，必须抓（info）
'''

_FIXTURE_GOOD = '''
try:
    import ujson as _json
except ImportError:
    import json as _json

# 「默认值 + 失败回退」是标准写法，绝不能被判成 ERROR
FLAG = True
try:
    import _nothing_here as _dep
    _dep.ok()
except Exception:
    FLAG = False

if True:
    BRANCH_VAR = 1
else:
    BRANCH_VAR = 2

def f():
    CN_NUM = {"一": 1}      # 函数内局部，不算
    return CN_NUM

if __name__ == "__main__":
    MODE = "a"
    MODE = "b"               # main 块内，不算
'''


def selfcheck():
    import tempfile
    ok = True

    def run_on(src, tag):
        fd, p = tempfile.mkstemp(suffix='.py')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                fh.write(src)
            return scan_file(p, quiet=True)
        finally:
            os.unlink(p)

    # 正向：脏文件必须抓到 3 件（dup_assign / dup_def / shadow_builtin）
    errs, infos = run_on(_FIXTURE_BAD, 'bad')
    kinds = {e[1] for e in errs}
    info_kinds = {i[1] for i in infos}
    c1 = "dup_assign" in kinds
    c2 = "dup_def" in kinds
    c3 = "shadow_builtin" in info_kinds
    print(f"  正向1 CN_NUM 重复赋值被抓到 ......... {'✅' if c1 else '❌'}")
    print(f"  正向2 同名 def 覆盖被抓到 ........... {'✅' if c2 else '❌'}")
    print(f"  正向3 撞内建名被抓到 ............... {'✅' if c3 else '❌'}")
    ok = ok and c1 and c2 and c3

    # 反向：干净文件不许误报 ERROR（含「默认值+回退」这种标准写法）
    errs2, infos2 = run_on(_FIXTURE_GOOD, 'good')
    c4 = len(errs2) == 0
    print(f"  反向1 干净文件零误报 ................ {'✅' if c4 else '❌'} "
          f"{'' if c4 else '误报：' + str([e[1] for e in errs2])}")
    ok = ok and c4

    # 反向2：真目录扫描不该炸
    files = collect_files(".")
    c5 = len(files) > 0
    print(f"  反向2 目录扫描可用（{len(files)} 个 .py）.. {'✅' if c5 else '❌'}")
    ok = ok and c5

    print(f"\n  自测结果：{'✅ 全过' if ok else '❌ 有失败'}")
    return 0 if ok else 2


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="模块级符号覆盖检查器")
    ap.add_argument('--file', help='只查一个文件')
    ap.add_argument('--selfcheck', action='store_true', help='内置 fixture 双向自测')
    ap.add_argument('--quiet', action='store_true', help='只报 ERROR 不报 INFO')
    args = ap.parse_args()

    if args.selfcheck:
        print("symbol_guard 双向自测（正向必抓到 / 反向不许误报）")
        return selfcheck()

    files = [args.file] if args.file else collect_files(".")
    if not files:
        print("没有找到 .py 文件")
        return 0

    all_errors, all_infos = [], []
    for f in files:
        e, i = scan_file(f, quiet=args.quiet)
        all_errors.extend(e)
        all_infos.extend(i)

    print(f"符号覆盖检查：{len(files)} 个 .py 文件")
    print(f"  ERROR {len(all_errors)} ｜ INFO {len(all_infos)}\n")

    for path, kind, line, msg in all_errors:
        print(f"  ❌ [{kind}] {path}:{line}\n     {msg}")
    if all_errors:
        print()
    if not args.quiet:
        for path, kind, line, msg in all_infos:
            print(f"  ℹ️  [{kind}] {path}:{line}\n     {msg}")

    if not all_errors and not all_infos:
        print("  ✅ 未发现模块级符号覆盖")
    elif not all_errors:
        print("\n  结论：无 ERROR 级覆盖（INFO 多为有意写法）")

    return 1 if all_errors else 0


if __name__ == '__main__':
    sys.exit(main())
