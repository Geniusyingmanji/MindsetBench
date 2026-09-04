# far35：远域同 mindset 硬题第二批构造报告

日期：2026-09-04。在 [`far20`](far20-report.md) 的四个家族之上新增三个家族、15 题，合计七个家族、35 题，
全部 `split: calibration`，仍按 [`FAR_TRANSFER_PROTOCOL.md`](FAR_TRANSFER_PROTOCOL.md) 构造。尚未进行模型校准。

## 1. 新增的三个家族

| 家族 | mindset | source 域 | L2 / L3 / L4 目标域 | 答案形式 | 预注册诱饵 |
| --- | --- | --- | --- | --- | --- |
| `far-delayed-feedback-v1`（P3） | 有时滞时按当前误差足额修正会越过目标并来回摆动 | 老式淋浴的水温调节 | 备件仓补货（两周到货）/ 药物浓度滴定（每期消散两成）/ 五车跟驰（一秒反应延迟） | 系数加稳定步数；稳态与维持量；系数加末车减速幅度 | 差多少补多少、一步到位 |
| `far-selection-extreme-v1`（P1） | 许多相似单位中的极值本身不是证据 | 连锁门店差评榜首 | 教育局统考通报 / 规模不等学校的比例排名 / 校招最高分者的入职预测 | 是否处置加门槛；期望题数 | 把榜首当作事先指定的单位 |
| `far-threshold-cascade-v1`（P3） | 扩散的终点由门槛分布的缺口决定而非平均门槛 | 两个镇的抗议集会 | 银行挤兑简报 / 环形村落的滴灌推广（局部邻域）/ 长梁支柱的荷载再分配 | 两个场景的最终数量 | 用平均门槛一次性筛人、总承载力够就不倒 |

L3 的 broken relation 分别是：被调节量自行消散（比例修正停在 60，需维持量 20）；单位规模不等（同一比例在大校几乎不可能，
须按各校规模分别折算再合并，结论方向反转）；门槛只对两侧各两户计数（同样两户种子，相邻扩到全村、相对停在两户）。
L4 更换 Model：五个带延迟环节串联的幅度传递、离散先验下的分数回缩、连续荷载向最近完好柱的再分配。

## 2. 表面距离与静态验证

`mb audit data/manifests/far35.json --surface-table` 中新增家族 L2–L4 的 source/target 字符 bigram Jaccard：

| 家族 | L2 | L3 | L4 |
| --- | ---: | ---: | ---: |
| delayed-feedback | 0.02 | 0.02 | 0.08 |
| selection-extreme | 0.04 | 0.10 | 0.01 |
| threshold-cascade | 0.07 | 0.07 | 0.02 |

写作过程中三道 L2 的第一稿分别为 0.14、0.13、0.18，被闸门拦下；改写问句与规则的措辞后通过。这正是闸门的用途：
它不判断题目好坏，只阻止目标题借用 source 的句式。

| 检查 | 结果 |
| --- | --- |
| `mb validate data/manifests/far35.json --strict-v1` | 35 题，0 error |
| `mb validate-cards data/manifests/far35-cards.json data/manifests/far35.json` | 7 cards，0 error |
| `mb audit data/manifests/far35.json --require-complete-chains --surface` | 0 error |
| `mb verify all --dataset data/manifests/far35.json` | 35/35 PASS |

新增 verifier 的形式世界：延迟差分方程逐期模拟（进入区间、保持、不越过三项判据）与带消散系统的稳态；五辆车逐秒模拟并比较
末车与头车的最大减速幅度；精确二项分布的单单位尾概率与“至少一个达到”的合并概率、异质规模按各校人数取整后合并、
五种真实水平的似然加权；门槛固定点迭代、环形邻域逐轮模拟、最近完好柱荷载再分配。每个 verifier 同时核对 lure 世界确实
使 copy probe 成立。

## 3. 待校准

与 far20 相同，先跑 21 道 L2–L4 的 target-only 三样本：

```bash
export MINDSETBENCH_API_KEY='...'
scripts/run_far20_calibration.sh gpt-5.6-sol            # 默认数据集已改为 data/manifests/far35-hard.json
```

判读规则见协议第 7 节；三个新家族中 delayed-feedback 与 threshold-cascade 的 L0–L2 属于教科书模型，预计天花板
风险最高，若 target-only ≥ 80% 则按协议第 8 节把关键事实埋深、拆到多份材料，而不是加节点数。
