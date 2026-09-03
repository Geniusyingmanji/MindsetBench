# MindsetBench

MindsetBench 用于测量 LLM/agent 能否把一个问题中的认知图式迁移到新问题，而不只是复用表面模式。题目按迁移距离分为 L0–L4：从同域同型逐步增加重命名、关系编辑和跨表征变化。

每道题支持配对评测：

- `target-only`：只看目标题；
- `with-source`：附带共享正确图式的已解源题；
- `with-lure`：附带表面相似但结构错误的已解题；
- oracle/false mindset：只提供正确或错误的程序性规则，用于进一步诊断。

答案、结构约束和关键构造均可由程序验证。

## 当前任务

类型化开发集包含以下主要范式：

| 范式 | 测量内容 | 代表 case |
| --- | --- | --- |
| P2 | 参数变化与系统响应的灵敏度 | [`FORMAL-P2-SENS-L1-01`](data/v1/formal-p2-sensitivity-chain.yaml) |
| P3 | 因果路径、干预与效应传播 | [`FORMAL-P3-CAUSAL-L1-01`](data/v1/formal-p3-causal-chain.yaml) |
| P4 | 规则闭包和异常传播 | [`FORMAL-P4-CLOSURE-L1-01`](data/v1/formal-p4-closure-chain.yaml) |
| HSS/P4 | 默认规范、成对例外与先例关系恢复 | [`HSS-P4-NORM-PRECEDENT-L4-01`](data/v1/hss-p4-norm-precedent-chain.yaml) |
| HSS/P7 | 证据谱系去重、攻击传播与独立性修订 | [`HSS-P7-ARG-EVIDENCE-L4-01`](data/v1/hss-p7-argument-evidence-chain.yaml) |
| HSS/P6 | 因果角色系统映射与致命关系反转 | [`HSS-P6-HIST-ANALOGY-L4-01`](data/v1/hss-p6-historical-analogy-chain.yaml) |
| HSS/P8 | 可信承诺、分离信号与成本承担关系 | [`HSS-P8-INST-MECHANISM-L4-01`](data/v1/hss-p8-institutional-mechanism-chain.yaml) |
| HSS/Active | 决策相关的单步查询与成本敏感条件策略 | [`HSS-ADAPTIVE-P7-ORAL-L4-01`](data/v1/hss-adaptive-policy-seeds.yaml) |
| P5 | 有状态操作规划、潜在操作恢复与最优性证明 | [`FORMAL-P5-CERT-POLICY-JOINT-01`](data/v1/formal-p5-certificate-policy-joint.yaml) |
| P6 | 多对象联合图对齐 | [`FORMAL-P6-ALIGN-L1-01`](data/v1/formal-p6-alignment-chain.yaml) |

`Formal25/30/35` 是累计校准包名称，数字表示题目数量，并不是三种独立方法：

| 数据包 | 内容 |
| --- | --- |
| `formal25` | P2/P3/P4/P5/P6 五条 L0–L4 链，共 25 题 |
| `formal30` | `formal25` + 一条“潜在操作恢复”P5 链，共 30 题 |
| `formal35` | `formal30` + 一条“规划最优性证书”P5 链，共 35 题 |

其中：

- **潜在操作与跨表征规划**：模型先从日志中恢复匿名操作规则，再把规则迁移到另一种表示中完成规划；最高难度会在“位排列/异或”和“集合取位/对称差”之间转换。
- **有状态规划最优性证书**：模型不仅要找一条可行路径，还要报告最优成本、唯一最优路径、低成本零命中、最优层路径数，以及次优成本和路径数。

它们目前都是 calibration/challenge 数据，用于定位失败模式，不代表已经得到稳定的正迁移结论。

## Humanities/Social-20

现有正式题仍偏系数计算、组合枚举和路径搜索。`hss20` 已完成四条人文社科 L0–L4 链，共 20 题：规范与判例、论证与证据、历史类比、制度机制。20/20 为非数值结构答案并具有可执行 verifier；8 个 L3/L4 均跨文体、跨表征，其中技术→HSS 与 HSS→HSS 各半。GPT-5.6 三样本校准中三条件均为 100%，所以它们目前是 sanity/calibration 资产，不是正式高难集。

L3/L4 的 source 与 target 必须同时跨学科、跨文体和跨表征，不能只是替换名词；至少 16/20 使用标签、集合、排序、三值或角色映射作答，全部保留可执行 verifier。

难度将主要来自“从自然语言材料恢复关系—判断哪些关系可迁移—适配一条被改变的核心关系”，而不是增加算术长度。完整目标、候选题对和代码交付计划见 [`docs/HUMANITIES_SOCIAL_EXPANSION.md`](docs/HUMANITIES_SOCIAL_EXPANSION.md)。

新增 `hss-active8`：4 题把输出改为单次档案/实验选择，4 题要求提交两阶段自适应策略树，覆盖残卷、舞谱、
广播剧、木偶戏、装置艺术、口传史和外交礼物。每题的正确 mindset 与表面捷径都会导出不同首查；不过
GPT-5.6-sol 的两轮 target-only 预筛仍全部正确，因此这 8 题也暂归 calibration。完整构造和下一步交互式方向见
[`docs/active-learning-report.md`](docs/active-learning-report.md)。

## 题目示例

**Case 1：线性因果总效应（P3/L1）**

```text
A = 2T + ε_A
B = -T + 3A + ε_B
Y = -2T + 4A + 5B + ε_Y
求 ∂E[Y | do(T=t)] / ∂t。
```

正确图式是沿 DAG 传播响应：`d_A=2`，`d_B=-1+3×2=5`，所以答案为
`-2+4×2+5×5=31`。`with-source` 提供同类已解结构；`with-lure` 使用同一张图却只数四条路径，答案为 4，用于检测模型是否忽略边权。完整 case 见 [`FORMAL-P3-CAUSAL-L1-01`](data/v1/formal-p3-causal-chain.yaml)。

**Case 2：属性谓词联合规划（P5/L4）**

目标给出 16 张带前置、禁止、置位、清除和费用的操作卡。模型先根据三条集合谓词分别定位唯一卡，再从完整基线独立冻结该卡，计算最优与次优路径层：

```text
α → K13：最优成本 17，次优成本 18，次优路径 2 条
β → K2 ：最优成本 17，次优成本 19，次优路径 3 条
γ → K6 ：最优成本 18，次优成本 19，次优路径 3 条
```

三次冻结不能叠加；路径首次满足完整目标就必须停止。最终答案包含 3 个七段 block，共 21 段。完整题面见 [`FORMAL-P5-CERT-POLICY-JOINT-01`](data/v1/formal-p5-certificate-policy-joint.yaml)。

**更多紧凑 case**

| Case | 目标题摘要 | Gold | Lure / 常见错误 |
| --- | --- | --- | --- |
| [`P2/L1`](data/v1/formal-p2-sensitivity-chain.yaml) | 四个节点各选一条带权出边，全部最终汇入根，求恰好两条蓝边的方案数 | `500` | 允许内部四环，得到 `548` |
| [`P4/L1`](data/v1/formal-p4-closure-chain.yaml) | 对四份申请递归应用三层派生规则，再判断未授权违规 | `P2` | 只检查一轮初始事实，误报 `P1;P2;P3` |
| [`P6/L1`](data/v1/formal-p6-alignment-chain.yaml) | 在含噪声边的两张图间联合恢复节点映射与关系码字典 | `B1;B2;%;@` | 先按出现顺序固定码字典，得到 `B2;B1;@;%` |

## 评测快照

以下均为 GPT-5.6-sol 的小样本 calibration 结果，不是排行榜成绩：

| 实验 | 条件 | 样本 | 整题 exact | 逐段正确 | 7 段 block |
| --- | --- | ---: | ---: | ---: | ---: |
| Formal35 单样本预筛 | target-only | 5 题×1 | 4/5 | 29/30 | — |
| 联合题 solved-reference | target-only | 3 | 0/3 | 50/63 | 1/9 |
| 联合题 solved-reference | with-source | 3 | 0/3 | 34/63 | 2/9 |
| 联合题 solved-reference | with-lure | 3 | 1/3 | 54/63 | 4/9 |
| 联合题 procedure-only | oracle mindset | 3 | 0/3 | 52/63 | 2/9 |
| 联合题 procedure-only | false mindset | 3 | 0/3 | 44/63 | 0/9 |
| HSS20 L3/L4 v2 | target-only | 8题×3 | 24/24 | 168/168 | — |
| HSS20 L3/L4 v2 | with-source | 8题×3 | 24/24 | 168/168 | — |
| HSS20 L3/L4 v2 | with-lure | 8题×3 | 24/24 | 168/168 | — |
| HSS 单步主动查询 | target-only | 4题×3 | 12/12 | 48/48 | — |
| HSS 两阶段条件策略 | target-only | 4题×3 | 12/12 | 84/84 | — |

Formal35 的 L0–L3 已接近天花板。HSS20 在修复答案格式契约并扩充关系干扰后仍是 100%，说明纯文本加长不能产生迁移难度。联合题中 solved source 没有稳定增益；procedure-only oracle 相对 false mindset 改善局部搜索，但整题 exact 仍为 0。当前所有结果都不足以声称已实现稳定 schema transfer。

## 快速开始

需要 Python 3.11+：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

.venv/bin/mb validate data/manifests/formal35.json --strict-v1
.venv/bin/mb validate-cards \
  data/manifests/formal35-cards.json \
  data/manifests/formal35.json
.venv/bin/mb audit data/manifests/formal35.json --require-complete-chains
.venv/bin/mb verify all --dataset data/manifests/formal35.json
.venv/bin/pytest -q
```

最新的属性谓词联合反事实题可单独验证：

```bash
.venv/bin/mb validate \
  data/manifests/formal-p5-certificate-policy-joint.json \
  --strict-v1
.venv/bin/mb audit data/manifests/formal-p5-certificate-policy-joint.json
.venv/bin/mb verify all \
  --dataset data/manifests/formal-p5-certificate-policy-joint.json
```

## 运行模型评测

API 凭据只通过环境变量或终端隐藏输入传入，不应写入命令参数、配置或结果库：

```bash
export MINDSETBENCH_API_KEY='...'

.venv/bin/mb run \
  --dataset data/manifests/formal35.json \
  --database artifacts/runs/example.sqlite \
  --experiment-id example-v1 \
  --model MODEL_ID \
  --endpoint https://example.com/v1/chat/completions

.venv/bin/mb report \
  --database artifacts/runs/example.sqlite \
  --experiment-id example-v1 \
  --calibration-gates \
  --min-samples 3
```

多段答案可用 `--part-details` 查看逐段结果；联合查询可用 `--part-group-size N` 按固定长度 block 计算 exact accuracy 和 coverage。运行结果写入可恢复的 SQLite，`artifacts/` 默认不进入 Git。

## 当前结论

- 显式规则题对强模型普遍偏简单，容易出现天花板效应。
- HSS20 的首轮假低分来自未明示的答案前缀；修复后 72/72 全对，现已明确降为 sanity/calibration。
- 远域换皮加主动查询仍不足：单步与两阶段策略共 24/24 全对；增加显式矩阵搜索只显著增加 tokens/延迟。
- 潜在操作题已跨多个同构实例复现难度，但 solved source 的正增益尚不稳定。
- 最新联合证书题稳定暴露了 first-hit stopping-time 错误：模型会把首次满足目标后的冗余操作误计为新路径。
- procedure-only oracle 能改善部分字段和答案完整性，但整题 exact 仍未改善，因此暂不声称稳定 schema transfer。

详细结果见[远域主动学习报告](docs/active-learning-report.md)、[Humanities/Social-20 报告](docs/hss20-report.md)、
[潜在操作报告](docs/formal30-report.md)、[最优性证书报告](docs/formal35-report.md)和
[属性谓词联合证书报告](docs/p5-certificate-policy-joint-report.md)。

## 仓库结构

```text
data/v1/             题目 YAML
data/manifests/      可组合的数据集清单
data/schema_cards/   范式与构造规范
src/mindsetbench/    校验、判分、runner、指标和 verifier
tests/               自动化测试
docs/                设计文档与实验报告
harness/             兼容旧版 85 题数据的接口
```

进一步阅读：[总体计划](PLAN.md)、[任务规范](docs/SPEC.md)、[构造方法](docs/METHODS.md)、[范式调研](docs/PARADIGMS.md)、[题库状态](data/CASE_STATUS.md)。
