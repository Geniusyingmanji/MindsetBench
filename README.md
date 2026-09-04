# MindsetBench

MindsetBench 测量 LLM/agent 能否把一个问题中的认知图式（mindset）迁移到一个表面完全不同的新问题，而不只是复用表面模式。
每个 mindset 以一条固定源的 L0–L4 链呈现：L0/L1 是同域锚点，L2 跨学科同构，L3 加入一条由领域语义带出的 broken relation，
L4 只保留 mindset 而更换 Model 与 Method。目标题只问该领域的自然决策，预注册的诱饵是该领域自己的标准做法，
答案全部由可执行 verifier 从形式世界重算。

每道题支持配对评测：

- `target-only`：只看目标题；
- `with-source`：附带共享正确图式的已解源题；
- `with-lure`：附带表面相似但结构错误的已解题；
- `with-both`：source 与 lure 同时给出、不标注、顺序由 case id 决定，测量表面竞争下的结构选择；
- oracle/false mindset（H0–H5 提示阶梯）：只提供正确或错误的程序性规则，用于剂量-响应诊断。

## 当前进度（2026-09-04）

### 正式校准候选：far50，十个远域家族、50 题

| 家族 | 范式 | mindset | L0 → L1 → L2 → L3 → L4 的领域 |
| --- | --- | --- | --- |
| `far-evidence-independence-v1` | P7 | 共享同一上游的一致信号只构成一份证据 | 方志考订 → 宗祠口述 → CI 合并门禁 → 手术排期审核 → 储罐联锁共因失效 |
| `far-negative-evidence-v1` | P2 | 未出现的预期信号与出现的信号同样切割候选集 | 食品溯源 → 院内感染 → 故障定位 → 编年史成书区间 → 红外相机路线 |
| `far-horizon-exploration-v1` | P1 | 试探的价值由其后剩余的可利用时间决定 | 越冬觅食 → 休渔渔场 → 施工队选择 → 术前用药 → 截止前投稿 |
| `far-credible-commitment-v1` | P8 | 承诺的可信度来自承诺人失去反悔的能力 | 接口停用 → 分成承诺 → 零售退差价 → 边境停火 → 罢工威胁收益 |
| `far-delayed-feedback-v1` | P3 | 有时滞时按当前误差足额修正会越过目标并摆动 | 淋浴调温 → 地暖温控 → 备件补货 → 药物滴定 → 五车跟驰 |
| `far-selection-extreme-v1` | P1 | 许多相似单位中的极值本身不是证据 | 门店差评 → 坐席投诉 → 统考通报 → 规模不等学校 → 校招录用预测 |
| `far-threshold-cascade-v1` | P3 | 扩散的终点由门槛分布的缺口决定而非平均门槛 | 抗议集会 → 业主联名 → 银行挤兑 → 环形村落推广 → 长梁支柱失效 |
| `far-invariant-reachability-v1` | P2 | 所有允许的操作都保持某个类别，不同类别的目标不可达 | 黑板消数 → 翻杯 → 象棋马步 → 舞蹈队形 → 三科目记账 |
| `far-selection-association-v1` | P3 | 按任一特征筛选出的子集会呈现全体中不存在的关联 | 镇医院住院 → 体检复查 → 校招面试 → 课程评论 → 恒星星表 |
| `far-scaling-law-v1` | P1 | 几何放大时面积按平方、体积按立方变化，比例外推失效 | 动物食量 → 鸟卵冷却 → 厨房晾汤 → 桥梁缩比模型 → 冷库造价 |

- 50/50 通过严格校验、schema card 校验、transfer-design 审计与表面距离闸门，50/50 有可执行 verifier；每个 lure 世界
  都由同一形式世界复算并确认使 copy probe 成立。
- `data/manifests/far50-hard.json` 是其中 30 道 L2–L4，是模型校准的首跑切片。
- **尚未进行模型校准。** 构造报告：[`far20`](docs/far20-report.md)、[`far35`](docs/far35-report.md)、[`far50`](docs/far50-report.md)；
  构造协议与十条规则：[`docs/FAR_TRANSFER_PROTOCOL.md`](docs/FAR_TRANSFER_PROTOCOL.md)。

### 题库口径

| 状态 | 类型化题数 | 内容 |
| --- | ---: | --- |
| calibration（far50） | 50 | 上表十个家族 |
| calibration（P5 算力型 challenge） | 19 | 潜在操作 L4、latent certificates/staged/seeds、certificate outages/policy-joint；用于定位搜索失败，不作为迁移距离证据 |
| sanity | 82 | `formal` 六条链、latent L0–L3、`expansion20`、`hss20`、`hss-active8`：目标题是 source 同一形式化系统的重命名或把形式结构原样写进题面，按 SPEC 只翻了 Surface，GPT-5.6-sol 上全部天花板；仍可运行、仍过 verifier，但不计入迁移距离统计 |
| dev（hard seeds） | 9 | AR 管线产出的早期 seed |
| legacy | 85 | `data/all.jsonl` 的原始题库，含七线程、两条固定源链与六条多跳链 |

详细分诊与降级理由见 [`data/CASE_STATUS.md`](data/CASE_STATUS.md)。

### 工具链

- `mb audit --surface`：对 calibration/test 的 L2+ 题做表面距离闸门。source 与 target 共享记法模板（边表、`LABEL=CODE`、
  长位串、竖线表）或字符 bigram Jaccard 大于 0.12 为 ERROR；lure 比 source 更远为 WARNING；`--surface-table` 打印逐题指标。
  阈值以旧题库校准：远域题在 0.01 到 0.09，改名链在 0.15 到 0.8。
- `with-both` 条件与指标 `with_both_gain`、`selection_loss`、`lure_answer_rate_by_condition`。
- `scripts/run_far20_calibration.sh`：预注册的两阶段校准跑批（先 target-only，再三个配对条件），默认数据集 `far50-hard.json`。

## 为什么重做（2026-09-03 复盘）

字符 bigram 审计显示，旧 85 题库的 L2/L3/L4 源目标文字重合为 0.09/0.04/0.03 且逐级下降，而 2026-09 的类型化扩展 L3/L4 为
0.16/0.22，比旧库 L1 还近；类型化 L3/L4 共 65 题中有 43 题，目标题与 source 的符号重合不低于与 lure 的重合。根因是那些链考的
是算法（矩阵树、SCM 传播、不动点闭包、最短路证书），算法需要同一种输入表示，所以目标题只能换名字，难度只能靠规模，于是
要么天花板、要么算力地板，source 给的是计算脚手架而不是框架。

far 系列改为考框架型 mindset：识别难、执行易；目标题写情境不写换装的形式系统；问句只问领域自然决策；诱饵是目标领域的标准做法；
关键事实靠可行性推断而非陈述；source 对目标在计算上无用。完整论证与规则见协议文档第 1、2 节。

## 题目示例

**证据独立性 L3（历史考订 → 临床治理）**：规程要求三份相互独立且结论一致的评估，独立的定义是签署前接触过一手证据且非主刀。
病程记录显示影像原片 14:00 起才可调阅，三位会诊在 11 到 12 点签署，因此只能依据同一份报告；独立评估只有影像科与
15:30 调阅原片的会诊两份。Gold 为不能排期，六项补救中只有让 A 调阅原片重签与外院专家远程阅片有效；诱饵是数六份一致意见。

**不变量与可达性 L3（黑板消数 → 舞蹈编排）**：8 名舞者只允许相邻三人轮转。只交换 1 号与 2 号的队形永远到不了，因为三人轮转
不改变排列的类别；1、2 互换加 3、4 互换的队形最少两次走位。verifier 对全部排列做广度优先搜索，恰有 20160 种可达。

## 历史校准快照（均为 GPT-5.6-sol 小样本，对象现已降为 sanity 或 challenge）

| 数据 | 条件 | 整题 exact | 结论 |
| --- | --- | ---: | --- |
| formal35 L0–L3 单样本预筛 | target-only | 4/5 | 天花板 |
| hss20 L3/L4 三条件三样本 | target-only / with-source / with-lure | 24/24 各 | 天花板，降为 sanity |
| hss-active8 两层 | target-only | 24/24 | 天花板，降为 sanity |
| P5 联合证书题 | target-only / with-source / with-lure | 0/3 各 | 算力地板，source 无增益，保留为 challenge |

这些结果只说明旧构造法测不到迁移；far50 的校准尚未开始，任何迁移增益结论都要等它跑完。

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

API 凭据只通过环境变量传入，不写入命令参数、配置或结果库。`matrixllm.alipay.com` 端点需要能访问 Alipay 办公网关的网络。

```bash
export MINDSETBENCH_API_KEY='...'
scripts/run_far20_calibration.sh gpt-5.6-sol                      # 两阶段：先 target-only，再 with-source / with-lure / with-both
scripts/run_far20_calibration.sh gpt-5.6-sol "$ENDPOINT" target   # 只跑 target-only 预筛，30 题 × 3 样本
DATASET=data/manifests/far20-hard.json scripts/run_far20_calibration.sh gpt-5.6-sol   # 只跑前四个家族
```

手动等价命令：

```bash
.venv/bin/mb run \
  --dataset data/manifests/far50-hard.json \
  --database artifacts/runs/far50-hard.sqlite \
  --experiment-id far50-hard-target-s3-v1 \
  --model gpt-5.6-sol \
  --endpoint https://matrixllm.alipay.com/v1/chat/completions \
  --conditions target-only --samples-per-item 3 --max-output-tokens 4096

.venv/bin/mb report \
  --database artifacts/runs/far50-hard.sqlite \
  --experiment-id far50-hard-target-s3-v1 \
  --calibration-gates --min-samples 3 --part-details
```

预注册判读（协议第 7 节）：整题 exact 落在 20% 到 60% 且错误回答集中命中 copy probe 的题保留并继续配对条件；
≥ 80% 的题降为 sanity 并按协议第 8 节调节难度旋钮（关键事实埋深、诱饵数字、跨文档拼接），而不是加规模。
`with-source − target-only`、`with_both_gain`、`selection_loss` 作为独立结果如实报告，不作为删题门槛。

## 仓库结构

```text
data/v1/             题目 YAML（far-*.yaml 为正式校准候选，其余多为 sanity）
data/manifests/      可组合的数据集清单（far50 / far50-cards / far50-hard 等）
data/schema_cards/   每个 mindset 的构造规范：必需关系、无效变体、五级计划、诱饵与 verifier 说明
src/mindsetbench/    校验、表面距离审计、判分、runner、指标和 verifier
scripts/             sanity 降级脚本与校准跑批脚本
tests/               自动化测试（236 项）
docs/                协议、构造报告、复盘与调研
harness/             兼容旧版 85 题数据的接口
```

进一步阅读：[总体计划](PLAN.md)、[构造协议](docs/FAR_TRANSFER_PROTOCOL.md)、[任务规范](docs/SPEC.md)、[构造方法](docs/METHODS.md)、
[范式调研](docs/PARADIGMS.md)、[题库状态](data/CASE_STATUS.md)。
