# P5 L4 分阶段诊断报告

## 为什么拆分

`FORMAL-P5-LATENT-L4-01` 同时要求跨越“位向量 ↔ 集合成员”表示、恢复九选八匿名码本，并独立求三个最低成本计划。GPT-5.5 在 16K 三条件均删失；32K target-only 虽能恢复唯一代码本并答对 Q1，却在 Q2/Q3 漏掉成本 11 真最优。

单一全对分无法区分三类能力：

1. `ID`：从有歧义观测联合恢复匿名码本与未使用候选；
2. `PLAN-ALL`：显式给出正确码本，只测三问完备规划；
3. `PLAN-Q1/Q2/Q3`：把每个查询单独运行，测实例难度与完成率。

因此 `data/v1/p5-latent-staged.yaml` 保留原 challenge 不变，新增五个 calibration diagnostics。它们不是降低 L4 的抽象关系，而是隔离误差来源。

## 可执行保证

- `DIAG-P5-LATENT-L4-ID-01`：13 项检查；位/集合目录与观测可解析，九选八码本唯一，`T3=G9`、`G4` 未使用，旧码本只在 T3 与未使用项两段不同。
- `DIAG-P5-LATENT-L4-PLAN-01`：15 项检查；显式新码本下三问唯一最优为 7/11/11，旧码本三计划在真实目标下全部错失目标。
- 三个单查询 probe：各 15 项检查；分别验证唯一最优、runner-up 成本、旧码本唯一最优及其错误终态。
- 篡改 G9 翻转集合或把显式 `T3=G9` 改回 G4，verifier 都会失败。

## 逐答案段指标

主分仍保持严格 exact match：所有 parts 全对才记为一题正确。新增指标只用于诊断，不替代主分：

- `part_accuracy`：按 condition 微平均的正确 parts / 预期 parts；
- `coverage`：实际解析到的 parts / 预期 parts；
- `completed_part_accuracy`：排除 `finish_reason=length` 后的逐段指标；
- `mb report --part-details`：按 case、condition、part index 展开正确率和覆盖率。

`GradeResult` 新增带默认值的 `expected_part_count` 与 `parsed_part_count`，旧 SQLite 可继续读取。grader 现在真正使用 `AnswerSpec.separator`；默认多段答案只以中英文分号切分，不再把路径内部逗号误当成额外答案段。

例如原 L4 32K 输出的 Q1 成本和路径正确、Q2/Q3 均错。旧结果库无需迁移即可报告全对准确率 0、part accuracy 2/6，而详细表显示 part 0/1 为 100%、part 2—5 为 0%。

## GPT-5.5 预筛结果

以下均为 Matrix OpenAI-compatible 端点的单样本诊断，不能代替三样本、多模型正式校准。

### 码本辨识

| 条件 | 结果 | parts | 输出 tokens | 延迟 |
| --- | --- | ---: | ---: | ---: |
| target-only | 正确 | 9/9 | 3,908 | 38.7s |
| with-source | 正确 | 9/9 | 4,343 | 41.0s |
| with-lure | 正确 | 9/9 | 3,740 | 34.4s |

ID 三条件全对且 lure 无影响，说明跨表征码本辨识对 GPT-5.5 已是 sanity ceiling，不应作为该模型的主要区分题。

### 显式码本规划

| 版本 | 问题 | 预算 | 结果 | 输出 tokens | 延迟 | 诊断 |
| --- | --- | ---: | --- | ---: | ---: | --- |
| 三问联合 | Q1—Q3 | 16K | 删失 | 16,384 | 208.9s | 无答案行 |
| 单问 v1 | Q1 | 16K | 语义正确、格式失败 | 10,573 | 122.4s | 成本与路径正确，但路径用逗号；格式契约随后修正 |
| 单问 v1 | Q2 | 16K | 删失 | 16,384 | 193.7s | 无答案行 |
| 单问 v1 | Q3 | 16K | 删失 | 16,384 | 190.4s | 无答案行 |
| 单问 32K v2 | Q1 | 32K | 正确 | 8,515 | 104.0s | 成本 7，唯一计划正确 |
| 单问 32K v2 | Q2 | 32K | 错误 | 27,724 | 376.8s | 找到可达成本 15 路径，漏掉成本 11 真最优 |
| 单问 32K v2 | Q3 | 32K | 正确 | 27,143 | 334.8s | 成本 11，唯一计划正确 |

32K 下三问完成率 100%、全对率 2/3、part accuracy 4/6。Q2 的错误路径经 verifier 重放确实到达目标，因此失败是全局最优性不足，不是状态变换手算或不可达幻觉。

### Q2 source/lure 配对

| 条件 | 结果 | 输出 | tokens | 延迟 |
| --- | --- | --- | ---: | ---: |
| target-only（独立预筛） | 错误 | `15;T6>T1>T2>T5>T8` | 27,724 | 376.8s |
| with-source | 正确 | `11;T5>T3>T2>T8>T6` | 15,616 | 216.6s |
| with-lure | 错误 | `无法确定` | 32,147 | 425.6s |

在 source/lure 同一 experiment 内，structural selectivity 为 +100pp。相关 source 不但使答案从错误变正确，还把输出 tokens 和延迟约减半；旧码本 lure 在近满 32K 后仍无法给出计划。target-only 来自单独 experiment，因此这仍是跨运行的单样本方向证据，不能报告为正式 paired source gain。

首次 Q2 paired 请求中 lure 遇到 provider HTTP 500，但 with-source trial 已写入 SQLite；用同一 experiment-id 续跑时 runner 跳过已有 source，只补缺失 lure，证明部分结果保存与断点恢复工作正常。

## 结论与下一步

- 保留 formal30 三问 L4 为 challenge/efficiency 轨；常规 16K 不把删失计作推理错误。
- ID probe 降为 sanity：它验证实现和表征映射，但对 GPT-5.5 缺少难度净空。
- Q2 单问是当前最有希望的迁移测量 seed：target-only 真实失败、with-source 正确、with-lure 失败，且错误路径可重放。
- 下一轮应对 Q2 进行至少 3 samples × 2 models 的三条件同 experiment 校准，并测试相同结构的参数变体，避免把单一实例记忆当作 schema transfer。
- Q1/Q3 可作为能力上界与效率对照，不能与 Q2 简单平均后声称达到接受窗。

## 复现

```bash
.venv/bin/mb validate data/manifests/p5-latent-staged.json --strict-v1
.venv/bin/mb audit data/manifests/p5-latent-staged.json
.venv/bin/mb verify all --dataset data/manifests/p5-latent-staged.json

.venv/bin/mb report \
  --database artifacts/runs/p5-latent-staged-gpt55.sqlite \
  --experiment-id p5-latent-staged-gpt55-singleq-target-32k-v2 \
  --part-details
```
