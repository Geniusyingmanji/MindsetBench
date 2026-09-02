# P5 L4 分阶段诊断报告

## 为什么拆分

`FORMAL-P5-LATENT-L4-01` 同时要求跨越“位向量 ↔ 集合成员”表示、恢复九选八匿名码本，并独立求三个最低成本计划。GPT-5.5 在 16K 三条件均删失；32K target-only 虽能恢复唯一代码本并答对 Q1，却在 Q2/Q3 漏掉成本 11 真最优。

单一全对分无法区分三类能力：

1. `ID`：从有歧义观测联合恢复匿名码本与未使用候选；
2. `PLAN-ALL`：显式给出正确码本，只测三问完备规划；
3. `PLAN-Q1/Q2/Q3`：把每个查询单独运行，测实例难度与完成率。

因此 `data/v1/p5-latent-staged.yaml` 保留原 challenge 不变，先新增五个 calibration diagnostics，再加入两个保持同一数学结构的 Q2 参数变体。它们不是降低 L4 的抽象关系，而是隔离误差来源并检验结论能否跨实例成立。

## 可执行保证

- `DIAG-P5-LATENT-L4-ID-01`：13 项检查；位/集合目录与观测可解析，九选八码本唯一，`T3=G9`、`G4` 未使用，旧码本只在 T3 与未使用项两段不同。
- `DIAG-P5-LATENT-L4-PLAN-01`：15 项检查；显式新码本下三问唯一最优为 7/11/11，旧码本三计划在真实目标下全部错失目标。
- 三个单查询 probe：各 15 项检查；分别验证唯一最优、runner-up 成本、旧码本唯一最优及其错误终态。
- 两个 Q2 参数变体：各 17 项检查；同时更换八个坐标、全部操作名和全部卡名，并保留唯一最优成本 11、runner-up 12/13 以及单关系更新。verifier 对九个操作逐一枚举 256 个状态，证明变体是原题的仿射共轭，而非手工复制答案。
- 篡改 G9 翻转集合或把显式 `T3=G9` 改回 G4，verifier 都会失败。

## 逐答案段指标

主分仍保持严格 exact match：所有 parts 全对才记为一题正确。新增指标只用于诊断，不替代主分：

- `part_accuracy`：按 condition 微平均的正确 parts / 预期 parts；
- `coverage`：实际解析到的 parts / 预期 parts；
- `completed_part_accuracy`：排除 `finish_reason=length` 后的逐段指标；
- `mb report --part-details`：按 case、condition、part index 展开正确率和覆盖率。
- `by_schema`：自动按 schema/source 设计切片，并在每个切片中报告 part accuracy、coverage、completion 与 copy rate，支持受控 source 消融。

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

### Q2 参数族与跨模型反证

为排除模型只适应了原始字母、坐标或答案字符串，新增 `V1/V2` 两题。两题分别对八维状态做不同坐标置换，将 `G/T` 全量重命名为 `R/U`、`W/V`，并把初始态、目标态、九个操作及旧码本计划一并共轭变换。两题的正确答案彼此不同，但都保持与原 Q2 相同的搜索几何：唯一最优成本 11，近邻成本 12/13，旧码本唯一最优成本 14。

单样本预筛结果如下。`source` 结果仅比较条件行为；三条件没有在同一个 experiment 中完整配对，因此不能据此估计正式 transfer gain。

| 模型 | 题集/条件 | 正确率 | 完成率 | 诊断 |
| --- | --- | ---: | ---: | --- |
| GPT-5.5 | V1/V2 target-only | 0/2 | 2/2 | V1 无法确定；V2 输出成本 9 且重复使用卡片，违反无重复约束 |
| GPT-5.5 | V1/V2 with-source | 0/2 | 1/2 | V1 在 32K 删失；V2 找到合法成本 19 路径，但漏掉成本 11 真最优 |
| GPT-5.4 | 原题+V1+V2 target-only | 0/3 | 3/3 | 均快速结束并给出不完整/次优搜索结果，平均 4,259 tokens、48.4s |
| GPT-5.4 | 原题 with-source | 0/1 | 1/1 | 输出 `14;T4>T6>T7>T5>T2>T3`，未找到成本 11 真最优 |
| GPT-5.4 | 原题 with-lure | 0/1 | 1/1 | 精确复制陈旧计划 `14;T3>T8>T7>T5>T2`，copy-probe 命中 |

GPT-5.5 的 V2 source 路径经 verifier 使用真实新码本重放，确实无重复、成本 19 并到达目标，因此它是“可达但非全局最优”的搜索失败。两道同构变体在 target-only 和 with-source 下均未答对，说明原 Q2 上观察到的 source 增益没有跨参数实例复现；原先的 +100pp 只能解释为实例级方向性结果，不能上升为稳定的 schema transfer。GPT-5.4 的 lure 精确复制则说明干扰示例能够诱发旧关系沿用，copy-probe 在这里提供了有效负迁移诊断。

## 结论与下一步

- 保留 formal30 三问 L4 为 challenge/efficiency 轨；常规 16K 不把删失计作推理错误。
- ID probe 降为 sanity：它验证实现和表征映射，但对 GPT-5.5 缺少难度净空。
- Q2 参数族稳定制造了全局最优性失败，适合保留为高难度规划 challenge；但 source 帮助尚不稳定，当前不能把它当作已经成立的迁移测量题。
- 暂不直接投入昂贵的 `3 samples × 2 models × 3 conditions` 正式校准。下一轮应先改造 source，使其表达可复用的搜索不变量或界证明，而不是仅提供一个源域实例；通过小样本 family screen 后再扩为完整配对实验。
- Q1/Q3 可作为能力上界与效率对照，不能与 Q2 简单平均后声称达到接受窗。

该 source 改造已进一步实现为六段最优性证书任务和路径对齐/路径解耦 source 消融。GPT-5.6-sol 的结果显示 source 能提升输出覆盖率和效率，但没有提升路径或证书正确率；路径解耦消除了精确 copy，却诱发数值证书形状复制。构造和完整结果见 `docs/p5-latent-certificate-report.md`。

## 复现

```bash
.venv/bin/mb validate data/manifests/p5-latent-staged.json --strict-v1
.venv/bin/mb audit data/manifests/p5-latent-staged.json
.venv/bin/mb verify all --dataset data/manifests/p5-latent-staged.json
.venv/bin/mb verify all --dataset data/manifests/p5-latent-staged-q2-family.json

.venv/bin/mb report \
  --database artifacts/runs/p5-latent-staged-gpt55.sqlite \
  --experiment-id p5-latent-staged-gpt55-singleq-target-32k-v2 \
  --part-details
```
