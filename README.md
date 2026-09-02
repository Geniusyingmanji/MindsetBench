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

| 范式 | 测量内容 |
| --- | --- |
| P2 | 参数变化与系统响应的灵敏度 |
| P3 | 因果路径、干预与效应传播 |
| P4 | 规则闭包和异常传播 |
| P5 | 有状态操作规划、潜在操作恢复与最优性证明 |
| P6 | 多对象联合图对齐 |

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
- 潜在操作题已跨多个同构实例复现难度，但 solved source 的正增益尚不稳定。
- 最新联合证书题稳定暴露了 first-hit stopping-time 错误：模型会把首次满足目标后的冗余操作误计为新路径。
- procedure-only oracle 能改善部分字段和答案完整性，但整题 exact 仍未改善，因此暂不声称稳定 schema transfer。

详细结果见[潜在操作报告](docs/formal30-report.md)、[最优性证书报告](docs/formal35-report.md)和[属性谓词联合证书报告](docs/p5-certificate-policy-joint-report.md)。

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
