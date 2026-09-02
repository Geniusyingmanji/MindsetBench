# P5 Q2 最优性证书与 source 消融报告

## 动机

原 Q2 参数族稳定诱发“找到可达路径但漏掉全局最优”或直接不可达的错误。只要求输出成本和卡串，无法判断模型是否真正完成了低成本层枚举，也无法区分路径发现、唯一性证明和次优边界三种能力。

本轮新增三道最优性证书题，以及三道目标题完全相同、只更换 solved source 查询的消融题：

- `base/V1/V2 CERT`：source 与目标都使用 Q2；源最优路径经对象映射后恰好形成目标编辑前的 stale plan；
- `base/V1/V2 CERT-DQ`：target problem、gold、lure 和 target-only prompt 与对应 CERT 题完全相同，但 source 改用不同初态/目标态的 Q1，避免源最优卡串直接映射为目标 Q2 stale plan。

每题最后输出六段：

```text
最优成本;唯一最优卡串;更低成本命中数;最优层命中数;次优成本;次优层命中数
```

source 证书分别为：

- 路径对齐 source：`14;S5>S6>S7>S1>S2;0;1;15;7`；
- 路径解耦 source：`12;S3>S7>S2>S4>S5;0;1;13;5`。

三个 target 经仿射共轭保持相同证书形状，但最优卡串不同：最优成本 11、低成本命中 0、最优层命中 1、次优成本 12、次优层命中 1。

## 可执行保证

`mindsetbench.verification.formal_p5_latent` 新增通用证书计算：

1. 节点保留状态、已用卡集合和完整有序路径；
2. 正成本一致代价枚举，卡片禁止重复；
3. 路径首次到达目标后终止，不再离开目标再返回；
4. 相同状态与已用集合上的等成本不同路径仍分别计数；
5. 搜索持续到首个严格更高的目标成本层，得到 runner-up 成本和多重性。

六道题各执行 19 项 verifier checks，包括题面与码本解析、九个操作各 256 状态共轭、source 机器可读证书、source 中等成本路径计数和首次命中语义、target/stale 两套精确路径计数、stale 计划真实重放及全部存储答案一致性。篡改次优路径数会被 verifier 拒绝。

测试还证明每对 `CERT/CERT-DQ` 的 target 对象、target-only prompt 文本和 prompt hash 完全相同，因此二者构成 source-only 消融。

## GPT-5.6-sol 三条件预筛

设置：Matrix OpenAI-compatible endpoint，temperature 0，最大输出 16,384 tokens，三个共轭 CERT target 各单样本。九个 trial 全部 `finish_reason=stop`，无删失。

| 条件 | exact | 正确 parts | coverage | 平均输出 tokens | 平均延迟 | copy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| target-only | 0/3 | 6/18 | 13/18 | 11,609 | 198.3s | 0/3 |
| with-source | 0/3 | 6/18 | 18/18 | 9,531 | 171.3s | 1/3 |
| with-lure | 0/3 | 7/18 | 13/18 | 11,905 | 208.3s | 1/3 |

结构化 source 把输出覆盖率从 72.2% 提到 100%，平均输出量减少约 18%，平均延迟减少约 14%，但没有增加正确 parts 或 exact accuracy。这是完成度/效率信号，不是推理迁移增益。

with-source 的实例级错误进一步说明原因：

- base 精确输出 stale 证书 `14;T3>T8>T7>T5>T2;0;1;15;7`；该路径在真实新码本下落到错误状态；
- V1 找到无重复、真实可达的成本 13 路径，但漏掉成本 11 唯一最优和成本 12 次优层；
- V2 输出成本 14 证书，但路径在真实码本下不可达。

因此 source 教会了输出契约和枚举语言，却没有让模型可靠执行完备搜索；在 base 上，源解的对象映射反而触发了精确 stale copy。

## 路径解耦 source 消融

随后在同批实验中仅运行 with-source，对三个路径对齐 source 和三个路径解耦 source 各单样本。六个 trial 均完成、exact 均为 0。

| source 设计 | exact | 正确 parts | coverage | copy |
| --- | ---: | ---: | ---: | ---: |
| Q2 路径对齐 | 0/3 | 4/18 | 13/18 | 1/3 |
| Q1 路径解耦 | 0/3 | 4/18 | 13/18 | 0/3 |

路径解耦消除了精确 copy，但没有改善正确率。V1/V2 都复用了 source 的数值证书形状 `12/0/1/13/5`，同时生成了真实目标不可达的卡串。这表明负迁移不只来自某一条 stale path，还来自把 source 的成本层统计当作可直接替换符号的模板。

同一组路径对齐 source 在两次 temperature-0 单样本运行中产生了不同错误类型，也再次说明不能用一次成功或失败估计稳定 transfer gain。

## Procedure-only oracle 配对

为进一步排除源答案的路径和数值形状，使用同一组三个 CERT target，在同一个 experiment 内配对 `target-only` 与 `h3-oracle-mindset`。oracle 只提供以下通用原则，不含任何源实例、卡名、成本或路径计数：正成本一致代价枚举完整有序路径，处理完最优层与首个次优目标层。

六个 trial 全部完成且无删失：

| 条件 | exact | 正确 parts | coverage | 平均输出 tokens | 平均延迟 |
| --- | ---: | ---: | ---: | ---: | ---: |
| target-only | 0/3 | 0/18 | 2/18 | 9,236 | 155.5s |
| procedure-only | 0/3 | 6/18 | 18/18 | 14,103 | 246.0s |

自动指标为 `oracle_mindset_gain=0`、`oracle_mindset_part_gain=+0.333`。procedure-only 让三题都输出完整六段，累计正确 6/18 个字段；代价是平均输出增加约 53%、延迟增加约 58%。逐路径重放显示：

- base 找到两条成本 19 的真实可达路径，且该成本层确有两条，但漏掉所有更低目标层；
- V1 报告成本 9，路径在真实码本下不可达；
- V2 找到真实可达的成本 12 runner-up，却漏掉唯一成本 11 计划。

这说明不含答案的过程提示能提高执行意愿、格式覆盖和部分成本层统计，却仍不能让 GPT-5.6-sol 完成八卡状态空间的低成本搜索；它属于部分过程迁移，不是最终任务成功。

## 结论与下一步

- 六段证书是有价值的诊断任务：它把路径、最优层唯一性和次优层边界拆成可评分 parts，并由穷举 verifier 给出真值。
- Q2 参数族对 GPT-5.6-sol 仍处于 challenge 难度；当前不满足正式校准所需的 target window，也没有 source gain。
- 路径解耦是必要但不充分的 source 设计。下一版应进一步消除可复制的成本/计数形状，例如使用不同卡数、不同成本谱和不同 runner-up 多重性的教学实例，或仅提供通用伪代码/不变量而不展示可映射的数值证书。
- procedure-only 已证明可以提升 part coverage，但计算宽度仍过高。下一步优先构造由小到大的 L0—L4 证书链，使较低等级落入可校准区间，同时保留 L4 八卡题作为 challenge，而不是继续给 L4 堆更长提示。
- 在新的 source family screen 至少两个变体出现真实可重放的最优路径前，不投入 `3 samples × 2 models × 3 conditions` 的正式预算。

## 复现

```bash
.venv/bin/mb validate data/manifests/p5-latent-certificates.json --strict-v1
.venv/bin/mb validate data/manifests/p5-latent-certificates-decoupled.json --strict-v1
.venv/bin/mb audit data/manifests/p5-latent-certificate-source-ablation.json
.venv/bin/mb verify all --dataset data/manifests/p5-latent-certificate-source-ablation.json

.venv/bin/mb report \
  --database artifacts/runs/p5-latent-certificates-gpt56sol.sqlite \
  --experiment-id p5-latent-certificates-gpt56sol-16k-v1 \
  --part-details

.venv/bin/mb report \
  --database artifacts/runs/p5-latent-certificate-source-ablation-gpt56sol.sqlite \
  --experiment-id p5-latent-certificate-source-ablation-gpt56sol-16k-v1

.venv/bin/mb report \
  --database artifacts/runs/p5-latent-certificates-gpt56sol-oracle.sqlite \
  --experiment-id p5-latent-certificates-gpt56sol-oracle-16k-v1 \
  --part-details
```

结果库位于 ignored 的 `artifacts/runs/`；API key 不进入命令参数、数据文件或 Git。
