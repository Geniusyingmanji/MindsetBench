# 题库分诊：各 case 当前状态

依据试点评测（docs/pilot-report.md）与构造纪律（PLAN.md §4.3）对全部 85 题分诊。状态标签：

- ready：可用，待阶段一统一难度实测校准后进入正式集；
- descaffold：题面脚手架化（把图式对应的公式/定律喂给了被测模型），须重写题面后方可用；
- audit：构建早于去脚手架纪律，需做一轮脚手架词汇审计（预期多数可过）；
- prototype-risk：原型为著名题/著名迁移案例，语料熟悉度可能抬高冷启动，保留但须实测、必要时换皮；
- dev：试点已用作进化集，划入 dev split，不进正式测试集。

## 汇总

| 状态 | 数量 | 范围 |
| --- | --- | --- |
| ready | 57 | 下表未特别标注的全部 |
| descaffold | 4 | chainE 全链（L1/L2/L3/L4-E-C1） |
| audit | 15 | multihopB / multihopG / multihopD 三条链 |
| prototype-risk | 3+4 | methodHist 3 题；另 MH-B-4、MH-F-1、L3-B-01、L2-B-02 单点标注 |
| dev | 6 | L0-A-01、L1-A-01、L1-B-01、L1-E-01、L1-F-01、L2-A-01 |

（prototype-risk 的 4 个单点与所属集合状态叠加；总数以 ready 口径不重复计。）

## 明细

### descaffold（必须重写，试点直接实证）

chainE 四题的题面明写"信号累积为 k·a、噪声标准差为 σ√k"甚至适配后的 √((r+b)t)，把"识别涨落模型"这一考察目标短路成算术；其中 L1-E-C1（46.25² 临界）与 L2-E-C1（38.75² 临界）还叠加算术精度陷阱，重写时一并把临界值挪离整数边界。重写模板参考 multihopE（同线程、已按去脚手架纪律构建并通过词汇审计）。

### audit（需脚手架词汇审计）

multihopB（不变量）、multihopG（混合亚群）、multihopD（止损决策）三条链共 15 题构建于去脚手架纪律确立之前。审计口径：题面不得出现"不变量/守恒/mod、混合/加权/亚群、期望值/贴现"等直接点破图式的词；只给原始事实。F/C/E 三条多跳链已过审计，可作对照模板。

### prototype-risk（保留，实测冷启动，偏高则换皮）

- methodHist 全部 3 题（L2-D-HI01 模拟退火、L3-A-HI02 Erlang B、L4-F-HI03 Black-Scholes）：历史迁移案例语料密度高，构造报告已自我提示；建议用作"污染对照组"——与同图式原创题的冷启动差即污染度估计。
- MH-B-4（三色归一游戏重参数化）、MH-F-1（鸡兔同笼→停车场，经典变体，但其定位本就是 L1 锚点，可接受）、L3-B-01（三变色龙改编）、L2-B-02（经典 mod-3 不变量改编）。

### dev（试点进化集，已曝光于评测流水线）

L0-A-01、L1-A-01、L1-B-01、L1-E-01、L1-F-01、L2-A-01——保留为 dev split（方法调试、进化阶段素材），不进正式测试集。

### ready 中的优先推荐（质量最高的子集）

- 完整链资产：chainA 全链（4 题，穷举验证、难度持平性说明齐全）；multihopF/C/E 三条链（15 题，去脚手架纪律下构建）；
- L3 照搬探针题：全部 L3 题都带程序验证的"照搬错误答案"，负迁移测量开箱即用；
- L4 多段式题：L4-A-01、L4-D-01、L4-E-01、L4-F-01、L4-G-01 等（建模选择+数值两段判分，防蒙对）；
- 构造方法研究集：methodAR / methodPair / methodMut 共 9 题（各自带方法元数据，可用于"构造方法是否影响题目质量"的分析）。

## 全库通用的待办（不分状态）

1. target-only 基线实测（强弱两档模型各 ≥4 样本），冷启动落在 20–60% 之外的回炉——试点显示对 Haiku 4.5 现有测试子集 10/11 偏易；
2. 跨模型独立解题复核（防单一生成器偏置）；
3. 难度单调性回归（同线程内 with-source 增益随等级递减，违者回查等级归属）。

## 类型化扩展资产（2026-09）

本页上方的 85 题分诊口径早于类型化扩展。新增资产单列如下：

| 数据包 | 题数 | 状态 | 实测结论 |
| --- | ---: | --- | --- |
| `hss20` | 20 | calibration | GPT-5.6-sol 的 8 个 L3/L4 三条件均为 100% |
| `hss-active-query4` | 4 | calibration | target-only 12/12，显式单步查询仍为天花板 |
| `hss-adaptive-policy4` | 4 | calibration | target-only 12/12，两阶段策略增加计算量但未产生净空 |

下一批只先构造 4 个自然语言查询生成/交互 seed；达到 20%–60% 冷启动门后再扩量。

## 2026-09-03 降级与远域批次

复盘结论见 [`docs/FAR_TRANSFER_PROTOCOL.md`](../docs/FAR_TRANSFER_PROTOCOL.md) 第 1 节：类型化扩展中的 L2–L4 目标题
要么是 source 同一形式化系统的重命名（共用边表/规则/操作卡模板），要么把关系图、规则层级或回复矩阵原样写进题面，
识别步骤为零。按 SPEC 五成分定义它们只翻了 Surface，且 GPT-5.6-sol 上均为天花板。现引入 `split: sanity`，
以下 82 题降级并写入 `history_note`，仍可运行、仍过 verifier，但不计入迁移距离统计：

| 数据 | 题数 | 降级依据 |
| --- | ---: | --- |
| `formal-p2/p3/p4/p5-planning/p5-certificate/p6` 六条链 | 30 | 重命名同构加单参数扰动；`mb audit --surface` 判定共享模板或文字重合超阈 |
| `formal-p5-latent-chain` L0–L3 | 4 | 同域或重命名码本恢复，难度来自枚举计算量；L4 保留为跨表征 challenge |
| `expansion20` | 20 | 首批题把 DAG、优先级、门控职责写进题面，target-only 无净空 |
| `hss20` 四条链 | 20 | 显式关系句与整理后规则，问句点名答案码；三条件 72/72 |
| `hss-active-query4` + `hss-adaptive-policy4` | 8 | 给出完整回复矩阵，只剩优化计算；target-only 24/24 |

仍为 `calibration` 的类型化资产只剩 P5 潜在操作 L4、latent certificates/staged/seeds 与 certificate outages/policy-joint
共 19 题；它们是算力型 challenge，用于定位搜索失败，不作为迁移距离证据。

新批次 `far20`（[`docs/far20-report.md`](../docs/far20-report.md)）：四个框架型 mindset 家族各一条 L0–L4 链，
L2–L4 跨学科、跨文体、跨表征且通过 `mb audit --surface` 闸门，20/20 有可执行 verifier；`far20-hard.json`
为其中 12 道 L2–L4。状态为 calibration，尚未做模型校准；晋级门见协议第 7 节。

| 状态 | 类型化题数 |
| --- | ---: |
| calibration（far20） | 20 |
| calibration（P5 算力型 challenge） | 19 |
| sanity | 82 |
| dev（hard seeds） | 9 |

## 2026-09-04 第二批远域家族（far35）

新增三个家族、15 题，全部 calibration：`far-delayed-feedback-v1`（P3，时滞下的过度修正）、`far-selection-extreme-v1`
（P1，极值选择效应）、`far-threshold-cascade-v1`（P3，门槛分布的缺口决定扩散终点）。`far35.json` 汇总七个家族 35 题，
`far35-hard.json` 为其中 21 道 L2–L4；三道 L2 的第一稿被 `mb audit --surface` 拦下并改写。报告见
[`docs/far35-report.md`](../docs/far35-report.md)。尚未做模型校准。

| 状态 | 类型化题数 |
| --- | ---: |
| calibration（far35） | 35 |
| calibration（P5 算力型 challenge） | 19 |
| sanity | 82 |
| dev（hard seeds） | 9 |
