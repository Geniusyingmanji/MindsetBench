# 正式扩展候选 25 题：P5 扩展与 2026-09-02 校准

这里的“候选”表示题目已经通过构造与真值门，但尚未通过正式难度门。五条链全部保留在 `calibration` split；单模型、单样本结果只能用于快速淘汰，不能据此冻结隐藏测试集。

## 当前组成

| 范式 | L3 迁移对象 | L4 broken relation | 可执行验证 |
| --- | --- | --- | --- |
| P2 | 带类型有向树谱与灵敏度多项式 | 一条边权变化 | 穷举 + 多项式行列式 |
| P3 | 线性干预响应路径 | 一条机制系数变化 | 拓扑动态规划 + 路径枚举 |
| P4 | 递归规则闭包 | 一条派生规则停用 | 最小闭包 + 一轮错误模型 |
| P5 | 带正负前置、置位/清除副作用和成本的操作网 | 一张恢复卡的登记效果变化 | 一致代价状态搜索 + 单调集合覆盖 |
| P6 | 节点与关系词典的联合对齐 | 一删一增交换最优映射 | 节点排列 × 关系排列穷举 |

`data/manifests/formal25.json` 聚合五条 L0–L4 链，`formal25-cards.json` 聚合五张 schema card。`formal-new20.json` 是 P3–P6 的 20 道新增题，`formal-new-high.json` 是四个新增范式共 8 道 L3/L4，`formal-p5-high.json` 只含 P5 两道高级题。

## P5 构造与验证

P5 不把操作当作独立标签，而把迁移对象定义为完整的状态转换关系：正前置、否定前置、置位、清除、成本、正终态和负终态。L3 对十个状态和十六张操作卡做双层重编号，同时保留唯一最优计划与三条只贵 1 的 runner-up；L4 只把 K3 的登记效果从 `v` 改为 `p`，旧最优因此无法恢复 `v`，新的 K8 旁路以 1 成本优势成为唯一最优。

验证器执行以下独立检查：

1. 从 source 紧凑表和 target 操作卡叙述反向解析完整实例，防止题面与求解器常量漂移。
2. 在“状态 × 已用操作集合”上做一致代价穷举，验证最优成本、最终状态、序列唯一性和 runner-up 边际。
3. 枚举所有操作子集，独立求解“忽略前置、清除和负目标”的单调错误模型；其唯一答案与 lure/copy-probe 一致。
4. L3 检查全部状态、操作、成本、前置和效果的完整同构；L4 检查仅 K3 一个登记效果不同，并重放旧计划确认失败。

高级题经历了三轮定向加难：

| 版本 | 主要变化 | GPT-5.5 target-only | 平均输出 | 平均延迟 |
| --- | --- | ---: | ---: | ---: |
| v1 | 8 状态、11 操作、显式状态表 | 2/2 | 2492.5 | 38.1 s |
| v2 | 10 状态、16 操作、三个一分 runner-up | 2/2 | 6450.5 | 98.7 s |
| v3 | 操作卡叙述；L4 不标出编辑位置 | 2/2 | 5826 | 81.0 s |

v2 首次运行在保存 L3 后遇到一次 VPN 隧道 503；使用完全相同配置和 experiment id 恢复后只补了 L4，证明断点去重有效。一次人为改变并发参数的恢复尝试被存储层拒绝；CLI 现已把这类配置漂移报告为无 traceback 的 `run configuration error`。

## 当前模型结论

2026-09-02，Matrix 的 GPT-5.5 完成了如下单样本预筛：

- P3/P4/P6 六道 L3/L4：6/6，平均 2357 输出 tokens、31.4 秒，无截断、无 copy-probe 命中；
- P5 v3 两道 L3/L4：2/2，平均 5826 输出 tokens、81.0 秒，无截断、无 copy-probe 命中；
- Matrix 对 `gpt-5.6` 返回 `404 Model does not exist`，因此当前校准模型仍是 GPT-5.5。

八道高级题在这次单样本预筛中合计 8/8，明显不在预注册的 20%–60% target-only 接受窗。P3/P4/P6 存在明显准确率天花板；P5 虽仍全对，但已表现为高推理成本。它们都只能作为 calibration/sanity 候选，不能宣称已达到正式高难标准。

下一轮不再单纯增加操作数量。P5 应转向“先从演示推断潜在操作语义，再规划”的双层任务，或加入条件效果与部分可观测状态；P3/P4/P6 则需要隐藏中间表示、增加多个结构上近等价假设，并让 source 提供可压缩搜索的证书。只有新的 target-only 预筛出现净空后，才值得运行三条件 × 三样本配对实验。

## 可复现命令

```bash
.venv/bin/mb validate data/manifests/formal25.json --strict-v1
.venv/bin/mb validate-cards \
  data/manifests/formal25-cards.json \
  data/manifests/formal25.json
.venv/bin/mb audit data/manifests/formal25.json --require-complete-chains
.venv/bin/mb verify all --dataset data/manifests/formal25.json

.venv/bin/mb plan-run \
  --dataset data/manifests/formal-new-high.json \
  --samples-per-item 3 \
  --max-output-tokens 8192
```

真实请求的密钥只通过环境变量传入；本地 SQLite 运行产物位于忽略目录 `artifacts/`，不进入 Git。
