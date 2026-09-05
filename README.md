# MindsetBench

MindsetBench 评测 LLM/agent 能否把一个任务中的认知图式（mindset）迁移到表面、领域、文体乃至任务接口均不同的新任务，
而不是记住题型、复用符号模板或获得额外计算脚手架。

项目的核心问题是：模型获得的是只能在原分布生效的 trick，还是能够跨域复用的 meta-skill？

## 评测单元

每个类型化 case 包含：

- `source`：展示正确 mindset 的已解源任务；
- `target`：只提供目标领域事实，不直接点名共享图式；
- `lure`：与 target 表面接近、但关系结构不同的已解干扰任务；
- `copy_probe`：机械照搬 lure 时会得到的确定错误答案；
- `mapping`：仅用于构造审计的对象映射、共享关系和 broken relation；
- `verification`：从形式世界重新计算 gold、lure 与关键中间量的可执行 verifier。

同一道题支持四个主要条件：

| 条件 | 输入 | 测量目标 |
| --- | --- | --- |
| `target-only` | 仅目标题 | 冷启动能力与难度净空 |
| `with-source` | 正确源题、解答和目标题 | 正迁移增益 |
| `with-lure` | 表面相似干扰题、解答和目标题 | 负迁移与照搬倾向 |
| `with-both` | source 与 lure 同时出现、顺序盲化 | 表面竞争下的结构选择能力 |

此外支持 H0–H5 提示阶梯、oracle/false mindset、随机无关 source、with-skill、hop-transfer 和 prefix-transfer。

## 迁移距离

| 等级 | 改变的内容 | 作用 |
| --- | --- | --- |
| L0 | 同域同型，仅换参数 | 性能与格式锚点 |
| L1 | 同域换表面实例 | 近域迁移 |
| L2 | 跨学科但 Model/Method 近同构 | 跨域同构迁移 |
| L3 | 加入领域语义产生的 broken relation，必须调整解法 | 适配能力 |
| L4 | Surface、Domain、Model、Method 均改变，只保留 Schema | 远类比迁移 |

分级采用 `Surface / Domain / Model / Method / Schema` 五成分定义。L3/L4 不能只是变量改名或把源题的边表、规则表、
回复矩阵原样搬进目标领域。

## 当前状态（2026-09-05）

仓库当前包含 171 道去重后的类型化题，以及 85 道 legacy 原始题库：

| split | 题数 | 当前用途 |
| --- | ---: | --- |
| `calibration` | 39 | 20 道 far50 L0/L1 链锚点；19 道 P5 搜索型 challenge，只诊断搜索失败 |
| `sanity` | 123 | 数据、grader 和 verifier 回归；已被 GPT-5.6-sol 做穿，不计入正式迁移结果 |
| `dev` | 9 | 早期 AR hard seeds，尚待按新协议重构 |

最近一次全仓验证为 `255 passed`。十个 far50 家族的 50/50 题均通过严格 schema、schema card、transfer-design、
表面距离审计和可执行 verifier。

目前**没有可用于 headline 迁移增益的高难 L2–L4 子集**。这是当前最重要的项目状态，而不是待隐藏的负结果。

## far50 远域家族

| 家族 | mindset | 跨域 case 链 |
| --- | --- | --- |
| `far-evidence-independence-v1` | 共用上游的一致信号只构成一份证据 | 方志考订 → 宗祠口述 → CI 门禁 → 手术审核 → 储罐联锁 |
| `far-negative-evidence-v1` | 缺失的预期信号也会排除候选 | 食品溯源 → 院感 → 故障定位 → 编年史断代 → 红外路线 |
| `far-horizon-exploration-v1` | 试探价值取决于结果返回后还有多少可利用时间 | 越冬觅食 → 渔场 → 施工队 → 术前用药 → 截稿投稿 |
| `far-credible-commitment-v1` | 可信承诺来自失去单方反悔能力 | 接口停用 → 分成 → 退差价 → 边境停火 → 罢工威胁 |
| `far-delayed-feedback-v1` | 有时滞时足额纠偏会越过目标并振荡 | 淋浴 → 地暖 → 备件补货 → 药物滴定 → 车队跟驰 |
| `far-selection-extreme-v1` | 多单位中的极值本身不是异常证据 | 门店差评 → 坐席投诉 → 统考 → 学校规模 → 校招预测 |
| `far-threshold-cascade-v1` | 级联终点由门槛分布缺口而非平均门槛决定 | 抗议 → 联名 → 挤兑 → 村落推广 → 长梁失效 |
| `far-invariant-reachability-v1` | 允许操作保持类别时，跨类别目标不可达 | 黑板消数 → 翻杯 → 马步 → 舞蹈队形 → 记账 |
| `far-selection-association-v1` | 按任一特征筛选会制造总体不存在的关联 | 住院 → 复查 → 面试 → 课程评论 → 恒星星表 |
| `far-scaling-law-v1` | 面积与体积的不同缩放率使比例外推失效 | 动物食量 → 鸟卵 → 晾汤 → 桥梁模型 → 冷库造价 |

`data/manifests/far50.json` 汇总完整 50 题；`far50-hard.json` 是历史 L2–L4 预筛切片，当前其中 30 题均为 sanity。

### 代表性 case

**证据独立性：历史考订 → 临床治理。** 三位会诊虽然签署了相同结论，但影像原片在签署后才开放，因此三人当时只能依赖同一份报告。
目标不是数签名，而是追踪证据根；只有真正独立接触原片的评估才能增加独立证据数。

**不变量：黑板操作 → 舞蹈编排。** 8 名舞者只允许相邻三人轮转。三循环保持排列奇偶性，所以只交换 1、2 的队形不可达；
同时交换 1、2 与 3、4 则可达。verifier 对 40320 个排列执行 BFS，确认恰有一半状态可达。

**主动查档：三色诊断 → 行政判例调阅。** source 直接给六种模式的探针响应表；target 改为六套文字化司法判准和五份封存判例。
模型必须先恢复反事实裁判矩阵，再求不等成本的两步 minimax 调阅树。

**相关公开行动：共源告警 → 历史建筑真伪评议。** 两位研究员共享一份目录线索、各有私人证言，再公开表态。
公开行动既不是独立原始证据，也不是共同线索的直接复制；需要对共享潜变量联合边缘化后再更新第三位专家的行动似然。

## 已有模型结论

以下均为 GPT-5.6-sol、温度 0 的小样本预筛：

| 数据切片 | 条件 | exact | 审计结论 |
| --- | --- | ---: | --- |
| `hss20` L3/L4 | target-only / with-source / with-lure | 各 24/24 | 显式关系结构导致天花板 |
| `hss-active8` | target-only | 24/24 | 给出完整回复矩阵后，只剩优化计算 |
| `far20-hard` 初筛 | target-only | 30/36 | 非满分来自格式、年份和快照批次口径；相关实验修复或作废 |
| far50 后六家族初筛 | target-only | 48/54 | 错误集中于时滞初态与时间线歧义；修复定点 6/6 |
| 新增制度边界、社会学习、潜机制 seeds | target-only | 37/37 | 模型真实完成推理，仍为天花板 |
| 社会学习 seeds | with-both | 9/9 | 正确 source 与 lure 同时出现也未造成选择错误 |
| P5 联合证书题 | 三个主要条件 | 各 0/3 | 算力地板，source 没有产生迁移增益 |

因此，静态封闭题目前呈现两端：识别易、执行易时是天花板；扩大状态空间后又变成算力地板。两者都不能干净测量 mindset transfer。
完整失败审计见 [`docs/far50-calibration-report.md`](docs/far50-calibration-report.md)。

## 下一阶段：改变任务接口

下一批不再机械扩展静态 L0–L4 链，而先实现 4–6 个 seed：

1. **部分可观测 episode**：模型先查询，环境再返回隐藏状态下的局部观测；
2. **内生查询后果**：公开听证导致证人协调，查档触发封存，破坏性检查消耗样本；
3. **决策相关学习**：评分最终行动、查询成本与 oracle regret，不要求无意义地识别全部状态；
4. **查询合成**：模型生成受约束的查询或干预，不只选择预写的 A–D；
5. **开放式方案迁移**：source 提供关系结构，target 生成方案，由隐藏 simulator/tests 评分。

这一方向借鉴 [arXiv:2605.11258](https://arxiv.org/abs/2605.11258) 的“关系抽取 → 跨域搜索 → 新方案”流程，
重点是迁移其开放式搜索范式，而不是复刻论文中的领域配对。

Seed gate：每题先运行 target-only 至少 5 次；只有成功率落在 20%–60%、错误中 copy-probe 命中率至少 50%，并且人工排除
格式、歧义和截断后，才扩成完整家族并运行 `with-source / with-lure / with-both`。`≥80%` 的 seed 直接转入 sanity。

## 快速开始

需要 Python 3.11+：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

.venv/bin/mb validate data/manifests/far50.json --strict-v1
.venv/bin/mb validate-cards data/manifests/far50-cards.json data/manifests/far50.json
.venv/bin/mb audit data/manifests/far50.json --require-complete-chains --surface-table
.venv/bin/mb verify all --dataset data/manifests/far50.json
.venv/bin/pytest -q
```

## 运行模型评测

API 凭据仅通过环境变量传入，不写入命令参数、配置文件或结果数据库。

```bash
export MINDSETBENCH_API_KEY='...'

.venv/bin/mb run \
  --dataset data/manifests/far50-hard.json \
  --database artifacts/runs/far50-screen.sqlite \
  --experiment-id far50-target-s3-v1 \
  --model gpt-5.6-sol \
  --endpoint https://matrixllm.alipay.com/v1/chat/completions \
  --conditions target-only \
  --samples-per-item 3 \
  --max-output-tokens 8192

.venv/bin/mb report \
  --database artifacts/runs/far50-screen.sqlite \
  --experiment-id far50-target-s3-v1 \
  --calibration-gates \
  --min-samples 3 \
  --part-details
```

结果库使用 SQLite，支持断点续跑；相同 experiment/model/case/condition/sample 不会重复写入。

主要指标：

- `transfer_gain = acc(with-source) - acc(target-only)`；
- `structural_selectivity = acc(with-source) - acc(with-lure)`；
- `with_both_gain = acc(with-both) - acc(target-only)`；
- `selection_loss = acc(with-source) - acc(with-both)`；
- 各条件的 `copy_probe_rate`、逐 part 正确率、完成率、token 和延迟。

## 质量控制

- Pydantic 类型化 schema 与严格 v1 校验；
- schema card 检查 mindset、线程、范式和 L0–L4 计划；
- `mb audit --surface` 检查字符重合、符号模板和 source/lure 相对距离；
- 每题 lure 与 copy probe 必须一致，且与 gold 不同；
- 可执行 verifier 重算 gold、诱饵答案和关键中间量；
- `answer_format` 与 gold 字段前缀静态一致性检查；
- 原始模型回答人工审计，禁止把格式错误、标注歧义或截断解释成推理难度。

## 仓库结构

```text
data/v1/             类型化题目 YAML
data/manifests/      可组合的数据集与复现实验切片
data/schema_cards/   mindset 构造契约与 L0–L4 计划
src/mindsetbench/    loader、validator、prompt、grader、runner、metrics、verifier
scripts/             校准跑批与数据维护脚本
tests/               自动化测试
docs/                规范、构造报告、校准审计和调研
harness/             legacy 85 题兼容接口
artifacts/runs/       本地 SQLite 实验库，默认不提交
```

## 文档索引

- [`PLAN.md`](PLAN.md)：总体目标与下一阶段 code plan；
- [`docs/FAR_TRANSFER_PROTOCOL.md`](docs/FAR_TRANSFER_PROTOCOL.md)：远域构造和 seed gate；
- [`docs/SPEC.md`](docs/SPEC.md)：难度定义、数据字段和评测协议；
- [`docs/METHODS.md`](docs/METHODS.md)：题目构造方法；
- [`docs/PARADIGMS.md`](docs/PARADIGMS.md)：P1–P9 范式；
- [`docs/far50-calibration-report.md`](docs/far50-calibration-report.md)：最新模型校准与失败审计；
- [`data/CASE_STATUS.md`](data/CASE_STATUS.md)：题目分层与降级历史。
