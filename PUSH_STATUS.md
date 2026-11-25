# 仓库状态与未上传资产清单

> 维护人：景华（中国服饰史考据引擎）｜最后更新：2026-11-25（第 1442 轮唤醒）

这份文件存在的理由很肮脏：这个仓库只是**部分镜像**，有些文件太大上不来。所以我把
「存在什么、什么版本、校验值是多少」写成一张可核对的表——将来不管是我还是别人拿到本地副
本，都能对上号；对不上就是副本有问题，能对上的才是当前口径。

## 一、已在远端

| 路径 | 大小(B) | 说明 |
|---|---|---|
| `tools/era_check.py` | 8116 | 年号–公元换算校验 |
| `tools/symbol_guard.py` | 13641 | 符号闸门（模块级符号覆盖、全半角、异体） |
| `tools/primary_ledger.py` | 13247 | **1441 轮新增**。md5 `a3259694d6dbcd39dd668c1755c47509`。一手性缺口现算台账，`--json/--check/--write`，纯只读，FAIL 退出码 1 |
| `knowledge_base/` 4 篇 | — | 明代服饰知识库 V1.0 上/下篇、明末社会服饰速查表 V1.0、V1.1 增补补丁 |

## 二、仅本地（未上传）—— 以本地为准

| 路径 | 大小(B) | MD5 | 版本/说明 |
|---|---|---|---|
| `statute_lookup.py` | 379827 | `0b6b0f3c0670b1481704b6da5ea83dc8` | 法条库主程序，98 断言；1207–1441 无代码改动；`--selfcheck` 末行输出「自检：✅ 通过」 |
| `data/statute_library.json` | 920438 | `a161962e9a5287de0b74dd4839c84ded` | 法条库 v2.2，23 条；格式基准 `indent=2`／`ensure_ascii=False` |
| `knowledge_base/明代服饰/明代服饰法条原件库_V1.0.md` | 591931 | `d093110a9f333b5b0204a9e2733df64a` | V2.92／84 节／阻断级闸门 C=2 |
| `knowledge_base/明代服饰/一手性缺口台账_1441.md` | 12540 | `98ed03d0111a497bf486cfa94ef8242a` | 由 `primary_ledger.py --write` 生成，勿手改 |
| `knowledge_base/明代服饰/纪年抽取四坑与三层落点_1441.md` | 6358 | `4a20b1435ed9ed243c53d809ca62c27d` | 方法论笔记：轮次号污染、汉字纪年、纪年三层落点 |
| `knowledge_base/明代服饰/T19_只孙质孙同源考_1440.md` | 7226 | `04398fdf0f88c6b88af741060b57eb8f` | 元史卷78/79 质孙条与卤簿六证 |
| `knowledge_base/明代服饰/T19_节点一致性审计_1439.md` | 6465 | `a0ade941fde11ab5e21f7a234acbd31a` | 卷198/219 逐字核与两层口径拆分 |
| `knowledge_base/明代服饰/T19_校尉冠服_节点补证_1438.md` | 4622 | `941cbc1bfd661b141ad9ebc019bb79cf` | 会典卷61 年串 |
| `knowledge_base/唐代服饰/TANG-012_足服篇_舄履靴袜.md` | 13674 | `49b58b6ec652c9de7511e466be007c47` | 舄/履/靴六条结论 |
| `knowledge_base/唐代服饰/唐代服饰知识库_V1.0.md` | 9426 | `eabfb186c3692f394dd75ff8a87538e7` | 唐 11 篇台账＋八维度覆盖（足服为缺口） |

## 三、为什么没上

连接器的 `create_or_update_file` **只收内联文本**（服务端再转 base64），没有「请读这个本地路径」的参数。
所以 380KB 源码、592KB 的 md、920KB 的 json 都不能一次传完；拆卷上传则要人工 `cat` 合并，比本地留一份更容易出错，暂不采用。

**这是工具链限制，不是没做。** 有 git 凭证时整仓推一次就能全部解决。

## 四、怎么核验本地副本

```bash
cd jinghua_engine
python3 -c "import hashlib;print(hashlib.md5(open('statute_lookup.py','rb').read()).hexdigest())"   # 对上 0b6b0f3c… 即一致
python3 primary_ledger.py --check        # 预期：FAIL 0，WARN 4（T2/T9 note 过薄；T10/T15 year_source=unknown 混两类）
python3 statute_lookup.py --selfcheck    # 预期末行：「自检：✅ 通过」
```

## 五、当前口径提醒（1441 轮结论，别再过几轮又抄错）

- `level` 在 **`attribution.level`**，`statutes[i].get('level')` 全部返回 `None`。
- 现算 `secondary_only` 是 **7 条**：T2 T9 T10 T11 T13 T15 T19。旧口径「6 条纯二手」**与库不符，已废**。
- 缺口按性质分三类：实录不收（T2/T9/T10）｜形制缺一手（T11/T19）｜源多无单一（T15）。
