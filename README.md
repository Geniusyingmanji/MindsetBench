# MindsetBench

测量 LLM/agent 的 mindset（认知图式）跨学科迁移能力的 benchmark：以迁移距离为连续自变量（L0 同域同型 → L4 跨域远类比），配对式三条件评测（target-only / with-source / with-lure），全部机器可判。核心用途：区分 self-evolving 系统学到的是 trick（表面捷径，跨域归零）还是 meta-skill（可迁移图式，衰减平缓）。

## 快速导航

| 想了解 | 看 |
| --- | --- |
| 总体计划（背景、动机、三轴设计、路线图） | PLAN.md |
| 难度五级定义、测量协议、案例 schema | docs/SPEC.md |
| 五种题目构造方法对比 | docs/METHODS.md |
| 数学建模之外的图式范式调研（P1–P9） | docs/PARADIGMS.md 及 docs/research/ |
| 六条多跳长链简介（测迁移传递性） | docs/multihop-chains.md |
| 自进化方法试点评测结果与教训 | docs/pilot-report.md |
| 哪些题可用、哪些需修 | data/CASE_STATUS.md |

## 目录结构

```
PLAN.md               总体计划
docs/                 设计文档与调研报告
data/
  all.jsonl           全部题目（机器可读汇总，由 validate.py 生成）
  CASE_STATUS.md      题库分诊（ready / descaffold / audit / prototype-risk / dev）
  cases/              各题集（人读版 .md + 机器可读 .jsonl 成对）
harness/
  grade.py            判分器（整数精确、小数容差、多段逐段）
  prompts.py          三条件提示构造器
  sample.json         试点样本定义
  results/            试点原始结果与经验库
scripts/
  validate.py         schema 校验 + 链衔接检查 + 重建 all.jsonl
```

## 数据格式

每题一行 JSON（data/cases/*.jsonl）：id、level（0–4）、thread（A–G 认知线程）、schema_name（共享图式一句话）、source（源题：domain/problem/solution/answer）、target（目标题：domain/problem/answer/answer_type/tolerance）、mapping（对象映射 + 共享关系 + 翻转成分）、lure（表面相似异结构的干扰源）、provenance、verified（验证方式）。链案例另有 chain 与 hop 字段。L3 起的 mapping.varied 中标注"照搬源解法会得到的错误答案"，作为负迁移探针。

## 使用

```bash
python3 scripts/validate.py                 # 校验题库并重建 data/all.jsonl
python3 harness/prompts.py L3-A-01 target-only   # 生成某题某条件的评测提示
```

判分：`from harness.grade import grade_item; grade_item(item, model_output)`；被测模型须在最后一行输出 `ANSWER: <答案>`。

## 现状

题库 85 题（L0×2 / L1×15 / L2×19 / L3×30 / L4×19），七条认知线程全覆盖 L1–L4；固定源链 ×2 + 多跳长链 ×6；全部答案（含照搬错误答案与 lure 答案）经独立脚本验证。分诊与已知问题见 data/CASE_STATUS.md，路线图见 PLAN.md 第 7 节。

## 开发版工具链

新的类型化工具链位于 `src/mindsetbench/`，保留原有 `harness/` 接口兼容。首个 vertical slice 覆盖 L0–L4 各一题，并提供结构校验、严格判分、核心提示条件、可执行答案验证、可恢复 SQLite runner 与基础迁移指标。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

.venv/bin/mb validate
.venv/bin/mb verify all
.venv/bin/mb smoke
.venv/bin/pytest -q
```

`mb validate --strict-v1` 会把旧版题目缺少的结构化 copy probe、lure 解答、显式 split、oracle hint 和 verifier 当作错误；普通 `mb validate` 维持旧数据兼容，并以 warning 形式给出迁移清单。

## 多范式扩展开发集

首批 P2/P3/P4/P6 扩展包含四条固定源 L0—L4 链，共 20 题：

```bash
.venv/bin/mb validate data/v1/expansion20.yaml --strict-v1
.venv/bin/mb validate-cards data/schema_cards/pilot-v1.yaml data/v1/expansion20.yaml
.venv/bin/mb verify all --dataset data/v1/expansion20.yaml
```

对应 schema cards 位于 `data/schema_cards/pilot-v1.yaml`，初测结果与难度分诊见 `docs/expansion20-report.md`。这批题已通过结构与答案验证，但强模型初测存在明显天花板效应，当前只作为 calibration/sanity 候选。

## AR-hard 迭代与正式扩展候选 25 题

基于类比推理“结构抽取—跨域映射—broken relation 适配”方法的 dev seeds 位于 `data/v1/hard-seeds.yaml`。经过多轮迭代，当前包含 P2 谱灵敏度、P3 因果路径、P4 规则闭包、P5 有状态操作规划和 P6 联合图对齐五条链；每个范式含 L0—L4 五题，共 25 个扩展候选：

```bash
.venv/bin/mb validate data/v1/hard-seeds.yaml --strict-v1
.venv/bin/mb verify all --dataset data/v1/hard-seeds.yaml

.venv/bin/mb validate data/v1/formal-p2-sensitivity-chain.yaml --strict-v1
.venv/bin/mb validate-cards \
  data/schema_cards/formal-p2-sensitivity-v1.yaml \
  data/v1/formal-p2-sensitivity-chain.yaml
.venv/bin/mb verify all --dataset data/v1/formal-p2-sensitivity-chain.yaml

.venv/bin/mb validate data/v1/formal-p3-causal-chain.yaml --strict-v1
.venv/bin/mb verify all --dataset data/v1/formal-p3-causal-chain.yaml

.venv/bin/mb validate data/v1/formal-p4-closure-chain.yaml --strict-v1
.venv/bin/mb verify all --dataset data/v1/formal-p4-closure-chain.yaml

.venv/bin/mb validate data/v1/formal-p6-alignment-chain.yaml --strict-v1
.venv/bin/mb verify all --dataset data/v1/formal-p6-alignment-chain.yaml

.venv/bin/mb validate data/v1/formal-p5-planning-chain.yaml --strict-v1
.venv/bin/mb verify all --dataset data/v1/formal-p5-planning-chain.yaml

# 无复制聚合：五条链 25 题、五张 schema card、构造硬门槛
.venv/bin/mb validate data/manifests/formal25.json --strict-v1
.venv/bin/mb validate-cards \
  data/manifests/formal25-cards.json \
  data/manifests/formal25.json
.venv/bin/mb audit data/manifests/formal25.json --require-complete-chains
.venv/bin/mb verify all --dataset data/manifests/formal25.json
```

构造协议见 `docs/AR_HARD_CONSTRUCTION.md`，P2 的每轮失败模式和多样本结果见 `docs/hard-seed-eval.md`，25 题的构造与最新校准状态见 `docs/formal25-report.md`。五条链仍置于 `calibration` split；GPT-5.5 单样本预筛对新增范式的 L3/L4 为 8/8，仍有天花板效应，不应提前混入隐藏 test split。

在显式 P5 规划仍表现出天花板后，下一轮已加入一个“歧义日志恢复匿名仿射操作 + broken relation 适配 + 三问最短规划”的 L4 hard seed：

```bash
.venv/bin/mb validate data/v1/p5-latent-seeds.yaml --strict-v1
.venv/bin/mb audit data/v1/p5-latent-seeds.yaml
.venv/bin/mb verify all --dataset data/manifests/p5-latent-seed.json
```

它仍属于 calibration；当前 GPT-5.5 target-only 有一次有效推理失败，paired 条件则在 16,384 输出 tokens 处删失，不能提前报告迁移增益。构造、真值与逐次诊断见 `docs/p5-latent-seed-report.md`。

## Formal30：潜在操作与跨表征规划

在 formal25 上新增 P5 潜在仿射操作 L0—L4 链后，统一 calibration bundle 扩为六条链、30 题和六张 schema card：

```bash
.venv/bin/mb validate data/manifests/formal30.json --strict-v1
.venv/bin/mb validate-cards \
  data/manifests/formal30-cards.json \
  data/manifests/formal30.json
.venv/bin/mb audit data/manifests/formal30.json --require-complete-chains
.venv/bin/mb verify all --dataset data/manifests/formal30.json
```

新链从 L0 的局部唯一日志逐级增加到 L1 的全局码本消歧、L2 的完整跨域重命名、L3 的单关系编辑和 L4 的“位排列+异或 ↔ 集合取位+对称差”跨表征迁移。GPT-5.5 的 32K 单样本可恢复 L4 唯一码本并答对 Q1，但在 Q2/Q3 选择成本 14 的次优路径而漏掉成本 11 真值；目前仍只适合作为 challenge calibration。完整结果与下一轮 staged 方案见 `docs/formal30-report.md`。

L4 已进一步拆成码本辨识、显式码本三问规划、三个单查询诊断题，以及两个经 256 状态穷举证明的 Q2 仿射共轭参数变体；原 challenge 题保持不变：

```bash
.venv/bin/mb validate data/manifests/p5-latent-staged.json --strict-v1
.venv/bin/mb audit data/manifests/p5-latent-staged.json
.venv/bin/mb verify all --dataset data/manifests/p5-latent-staged.json
.venv/bin/mb verify all --dataset data/manifests/p5-latent-staged-q2-family.json
```

实验汇总默认报告逐答案段 micro accuracy/coverage；需要定位具体 Q1/Q2/Q3 时使用 `mb report ... --part-details`。GPT-5.5 在原 Q2 的单样本中曾出现 target-only 次优、with-source 正确、with-lure“无法确定”，但两个同构变体的 target-only 与 with-source 均为 0/2；GPT-5.4 对原题和变体 target-only 也为 0/3，并在 lure 条件精确复制旧计划。因此 Q2 的难度已跨实例复现，而 source 增益尚未复现，不能报告为稳定 schema transfer。详见 `docs/p5-latent-staged-report.md`。

Q2 又扩展为三道六段最优性证书题，以及三道 target 完全相同、只替换 solved source 查询的消融题。每题验证最优路径、低成本零命中、最优层唯一性和次优层计数；`mb report` 新增 `by_schema` 切片。GPT-5.6-sol 单样本显示结构化 source 提升 coverage/效率但不提升正确率，路径解耦能消除精确 copy 但仍会复制源证书的数值形状。详见 `docs/p5-latent-certificate-report.md`。

不含任何源答案数值的 `h3-oracle-mindset` 配对也已加入自动分析：`mb report` 同时给出 exact `oracle_mindset_gain` 与 `oracle_mindset_part_gain`。本轮 exact gain 为 0，part gain 为 +33.3pp；提示促使模型输出完整证书并找到真实可达的高成本层/runner-up，但仍漏掉全局最优。

```bash
.venv/bin/mb validate data/manifests/p5-latent-certificates.json --strict-v1
.venv/bin/mb validate data/manifests/p5-latent-certificates-decoupled.json --strict-v1
.venv/bin/mb verify all --dataset data/manifests/p5-latent-certificate-source-ablation.json
```

## Formal35：有状态规划最优性证书

在 formal30 上新增第七条完整 L0—L4 链：要求同时回答最优成本、唯一最优有序路径、低成本零命中、最优层多重性、runner-up 成本和 runner-up 多重性。L3 是十状态十六操作的完整同构，L4 只编辑一项操作效果并使旧证书整体失效：

```bash
.venv/bin/mb validate data/v1/formal-p5-certificate-chain.yaml --strict-v1
.venv/bin/mb audit data/v1/formal-p5-certificate-chain.yaml --require-complete-chains
.venv/bin/mb verify all --dataset data/v1/formal-p5-certificate-chain.yaml

.venv/bin/mb validate data/manifests/formal35.json --strict-v1
.venv/bin/mb validate-cards data/manifests/formal35-cards.json data/manifests/formal35.json
.venv/bin/mb audit data/manifests/formal35.json --require-complete-chains
.venv/bin/mb verify all --dataset data/manifests/formal35.json
```

GPT-5.6-sol 单样本预筛在修复路径分隔符契约后为 target-only exact 4/5、逐段 29/30；L4 只错 runner-up 路径数。盲化的 L3/L4 paired 运行中 source 没有提升正确率，lure 则把 L4 从 5/6 段降至 1/6。该结果只用于难度诊断，尚不能估计稳定迁移增益。构造保证、泄露修复和逐条件结果见 `docs/formal35-report.md`。

L4 又派生出三个动作冻结反事实：分别只改变 runner-up 数量、清空旧 runner-up 层、直接击穿旧最优路径。独立 DFS 和 verifier 均通过，但 GPT-5.6-sol 两轮 target-only 都为 3/3；同标签全启用基线 lure 也意外成为有用 scaffold，因此这三题只保留为 counterfactual sanity/ablation。失败分析与后续谓词化联合查询方案见 `docs/p5-certificate-outage-report.md`。

```bash
.venv/bin/mb validate data/manifests/formal-p5-certificate-outages.json --strict-v1
.venv/bin/mb audit data/manifests/formal-p5-certificate-outages.json
.venv/bin/mb verify all --dataset data/manifests/formal-p5-certificate-outages.json
```

显式冻结形成天花板后，又加入一题更抽象的 21 段联合查询：先从三条集合关系谓词唯一识别 `K13/K2/K6`，再为三个互不叠加的冻结情形分别输出七段“卡号 + 双层证书”。source 只提供一个小型属性谓词示例；lure 与目标的卡号、路径和成本完全解耦；另有不含任何答案数值的 oracle/false mindset 对照：

```bash
.venv/bin/mb validate data/manifests/formal-p5-certificate-policy-joint.json --strict-v1
.venv/bin/mb audit data/manifests/formal-p5-certificate-policy-joint.json
.venv/bin/mb verify all --dataset data/manifests/formal-p5-certificate-policy-joint.json

# 把连续七段视为一个完整反事实 query block
.venv/bin/mb report \
  --database artifacts/runs/formal-p5-certificate-policy-gpt56sol.sqlite \
  --experiment-id EXPERIMENT_ID \
  --part-group-size 7
```

GPT-5.6-sol 三样本 target-only 为 exact 0/3、逐段 50/63、完整 query block 1/9；三次都正确识别谓词对应卡号，主要失败是把“最优路径已经首次命中目标后再追加 K3”误算成成本 18 runner-up。procedure-only oracle 没有带来整题 exact，但在配对 target/oracle 三样本中把逐段正确率从 50.8% 提至 87.3%、完整 block 从 1/9 提至 4/9；同实验 oracle-vs-false 对照另得到 +12.7pp part selectivity 和 +22.2pp block selectivity。由于 solved source 没有稳定增益，当前只能报告程序性提示的局部收益，不能报告稳定 schema transfer。详见[属性谓词联合证书报告](docs/p5-certificate-policy-joint-report.md)。

真实模型实验通过环境变量传入密钥，不把凭据写进命令参数、配置或结果库：

```bash
export MINDSETBENCH_API_KEY='...'
.venv/bin/mb run \
  --dataset data/v1/expansion20.yaml \
  --database artifacts/runs/example.sqlite \
  --experiment-id example-v1 \
  --model MODEL_ID \
  --endpoint https://example.com/v1/chat/completions
```

三条新链的 L3/L4 可用 `data/manifests/formal-new-high.json` 统一预筛。实验结束后可重复读取 SQLite，并应用预注册的 target window、source gain、structural selectivity 与覆盖率门槛：

```bash
.venv/bin/mb plan-run \
  --dataset data/manifests/formal-new-high.json \
  --samples-per-item 3 \
  --max-output-tokens 8192

.venv/bin/mb report \
  --database artifacts/runs/formal-new-high-gpt55.sqlite \
  --experiment-id formal-new-high-gpt55-paired-v1 \
  --calibration-gates \
  --min-samples 3
```
