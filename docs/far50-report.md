# far50：超远域同 mindset 硬题第三批构造报告

日期：2026-09-04。在 [`far35`](far35-report.md) 之上新增三个家族、15 题，合计十个家族、50 题，全部
`split: calibration`，按 [`FAR_TRANSFER_PROTOCOL.md`](FAR_TRANSFER_PROTOCOL.md) 构造。本批的选材标准比前两批更严：
同一 mindset 的五个实例必须落在互不相邻的知识共同体里，任何两级之间不共享学科、文体与对象类型。尚未进行模型校准。

## 1. 三个家族与它们跨越的领域

| 家族 | mindset | L0 → L1 → L2 → L3 → L4 的领域 | 答案形式 | 预注册诱饵 |
| --- | --- | --- | --- | --- |
| `far-invariant-reachability-v1`（P2） | 所有允许的操作都保持某个类别，不同类别的目标不可达 | 黑板消数 → 翻杯游戏 → 国际象棋马步 → 舞蹈队形轮转 → 小店三科目记账 | 能否到达加最小值或步数 | “看起来能凑出来” |
| `far-selection-association-v1`（P3） | 按任一特征筛选出的子集会呈现全体中不存在的关联 | 镇医院住院 → 体检复查名单 → 校招面试简报 → 在线课程评论复盘 → 有亮度门槛的恒星星表 | 全体关系、子集关系、能否推因果 | 把子集关联当全体规律 |
| `far-scaling-law-v1`（P1） | 几何放大时面积按平方、体积按立方变化，比例外推失效 | 哺乳动物食量 → 鸟卵冷却 → 厨房晾汤 → 桥梁缩比模型 → 冷库围护造价 | 比例、时间、可行性加临界倍数、单位造价 | 按比例外推 |

三个家族的 L3 都由领域语义带出 broken relation：三人轮转保持的是排列的类别而不是数字总和的奇偶；评论中的负相关不是
凭空造出而是把全体中的正相关翻了方向；桥梁模型的面积一侧是承载而体积一侧是荷载，问题从比例变为可行性与临界倍数。
L4 更换 Model：余额的整数线性组合替代二元类别；比值阈值下的协方差符号替代 2 乘 2 表；成本核算替代热平衡。

## 2. 表面距离与静态验证

`mb audit data/manifests/far50.json --surface-table` 中新增家族 L2–L4 的 source/target 字符 bigram Jaccard：

| 家族 | L2 | L3 | L4 |
| --- | ---: | ---: | ---: |
| invariant-reachability | 0.00 | 0.01 | 0.01 |
| selection-association | 0.10 | 0.11 | 0.07 |
| scaling-law | 0.05 | 0.05 | 0.02 |

selection-association 的三个目标都保留了“同时……只……只……两者都没有”这种 2 乘 2 人数表的说法，重合因此接近 0.12 的闸门；
这是该家族的形式世界决定的，人数表若再改写会损害可核算性，故保留并在此注明。

| 检查 | 结果 |
| --- | --- |
| `mb validate data/manifests/far50.json --strict-v1` | 50 题，0 error |
| `mb validate-cards data/manifests/far50-cards.json data/manifests/far50.json` | 10 cards，0 error |
| `mb audit data/manifests/far50.json --require-complete-chains --surface` | 0 error |
| `mb verify all --dataset data/manifests/far50.json` | 50/50 PASS |

新增 verifier 的形式世界：多重集与朝上杯数的可达状态搜索、棋盘广度优先搜索加同色格奇偶核对、8 名舞者全部排列的广度优先
搜索（恰有 20160 种可达，即一半）、账面线性组合判定加进货与付款各 0 到 120 的穷举交叉验证；2 乘 2 人数表的条件比例
方向与筛选重算、阈值网格上协方差的符号；精确分数的平方与立方比例、安全系数与单位造价。每个 lure 世界都由同一形式世界
复算并确认使 copy probe 成立。

## 3. 待校准

`far50-hard.json` 为 30 道 L2–L4。校准脚本默认数据集已改为它，target-only 三样本共 90 次调用：

```bash
export MINDSETBENCH_API_KEY='...'
scripts/run_far20_calibration.sh gpt-5.6-sol
```

判读规则见协议第 7 节。本批中 invariant-reachability 的 L0–L2 与 scaling-law 的 L0–L2 属于经典智力题与教科书模型，
天花板风险最高；selection-association 因人数表显式给出，识别难度主要落在“先问这些人是怎么被选进来的”这一步。
若 target-only ≥ 80%，按协议第 8 节把人数表拆进叙事、把筛选规则埋进制度描述，而不是加大表格。
