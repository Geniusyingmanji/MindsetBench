# AR-hard seeds 初步评测

日期：2026-08-31。模型端点仍未提供 GPT-5.6，本轮使用其可用的 `gpt-5.5`。

## 题目与验证

`data/v1/hard-seeds.yaml` 最初包含 P2、P3、P4、P6 各一个 L3 seed；当前在保留这四个锚点的基础上已扩展到 9 个 dev seeds。它们全部通过 strict-v1，并由位掩码穷举、后门调整集枚举、前向规则引擎、图映射穷举、布尔 Möbius 反演、Bareiss 行列式与多项式矩阵树定理等 verifier 复算。

## 2048-token 配对试验

| seed | target-only | with-source | with-lure | 解释 |
| --- | --- | --- | --- | --- |
| P2 | length | length | length | 三次均耗尽 2048 tokens 且无可见答案，属于截断 |
| P3 | 正确 | 正确 | 正确 | 仍过易，source 冗余 |
| P4 | 正确 | 正确 | 正确 | 仍过易，source 冗余 |
| P6 | 正确 | 正确 | 正确 | 仍过易，source 冗余 |

直接报告的 75% accuracy 会把 P2 截断混成错误，因此不应作为认知难度结论。

## P2 预算复测

在 8192-token 配对试验中：

- target-only 再次耗尽预算且未输出答案；
- with-source 正确，使用 5710 completion tokens；
- with-lure 也正确，使用 3897 completion tokens。

随后将 target-only 上限提高到 16384，重复请求在 2587 tokens 正确完成。由此可见结果对单次服务轨迹和预算敏感；且 lure 与 source 同样能提供足够的异或建模脚手架，无法证明结构选择性迁移。

## 分诊结论

四题均未达到正式扩展门槛：

- P3/P4/P6：target-only 无净空，需要隐藏整理后的结构、增加结构恢复或组合推理。
- P2：计算负荷已有提升，但 source 并不优于 lure，且单次完成率不稳定；需要让 lure 保留表面但破坏关键关系，而不是同样教授 GF(2) 表示。

因此这些题继续保留为 `dev` seed，尚不计入正式 20 题。下一轮应先修改四个 seed，直到至少出现可重复的 target-only 净空和正 structural selectivity，再派生 L0—L4。

## 第 2 轮：逐级增加抽象结构

后续预筛固定 `max_output_tokens=16384`、每条件 3 个样本。连续变异的 GPT-5.5 target-only 结果为：

| seed | 新增的抽象层 | target-only | 处理 |
| --- | --- | --- | --- |
| HARD-P2-L3-01 v2 | GF(2) 翻转 vs 单调集合覆盖 lure | 3/3 | 目标仍过易，降为锚点 |
| HARD-P6-L4-02 | 联合恢复节点映射和关系词典 | 3/3 | 存在满分同构，可沿锚点贪心扩展 |
| HARD-P2-L4-02 | 布尔偏序 Möbius 反演 | 3/3 | frontier 已稳定内化该算子 |
| HARD-P2-L4-03 | 后继场到带权有向树计数 | 3/3 | 矩阵树定理仍过稳定 |
| HARD-P2-L4-04 | 形式变量与树谱系数提取 | 3/3 | 难度已达 8k tokens，但准确率无净空 |
| HARD-P2-L4-05 | 重命名系统对齐 + 局部灵敏度迁移 | 1/3，其中 1 次 length | 进入配对评测 |

这一系列表明，把规模从 10 bit 扩到 64 个偏序状态、6 阶行列式或多项式行列式，只会增加计算长度。真正产生迁移净空的是：目标系统与已解 source 存在重命名同构，但有一条关系的参数发生变化；解题者需同时发现保留关系和 broken relation，才能复用 source 的灵敏度。

## HARD-P2-L4-05 配对结果

### GPT-5.5

| 条件 | 准确率 | 完成率 | 完成样本平均 tokens | 完成样本平均延迟 |
| --- | ---: | ---: | ---: | ---: |
| target-only | 1/3 | 2/3 | 12057 | 165294 ms |
| with-source | 3/3 | 3/3 | 1223 | 22457 ms |
| with-lure | 2/3 | 3/3 | 10313 | 131492 ms |

- 原始配对 source gain：+66.7 个百分点。
- 只对完成样本的 source gain：+50 个百分点。
- source 相对 lure 的 structural selectivity：+33.3 个百分点。
- source 三次都正确识别 `U3→U6 ↔ H→G`，用 `P₄+5Q₄` 完成局部更新；平均输出 token 比 target-only 完成样本低约 89.9%。
- lure 并没有简单导致复制 985；2/3 样本仍能自行重算正确，因此该 lure 的负迁移强度还可继续调整。

### GPT-5.4

GPT-5.4 的 target-only、with-source、with-lure 均为 0/3，且 9 次全部完成。三次 with-source 都忽略了参考解中明示给出的 `P₄` 和 `Q₄`，重新构造并误算八阶多项式行列式。这是类比识别失败，而非算力截断。因此当前 seed 的状态为：

- GPT-5.5 frontier 单模型初步通过；
- 跨模型方向一致性未通过；
- 不应直接宣布为正式定级题，应保留为能力分层 seed 并继续调整 source 可发现性。

`gpt-5.4-pro` 虽出现在端点 `/v1/models` 列表中，但对 `/v1/chat/completions` 返回 `unsupported_operation`，未产生试次，不计入模型比较。

## 评测实现修正

`summarize_transfer` 现同时报告：

- 原始准确率与原始配对增益，用于完整复现；
- 截断作为 censored 后的完成样本准确率与配对增益；
- 各条件的完成率；
- 只在完成样本上计算的平均/中位输出 tokens 和延迟。

提供者在模型不支持当前 API 操作时抛出安全错误且不伪造 trial；这与 `finish_reason=length` 及已完成但答错的试次分开。

## v1.1：移除取模算术混杂

GPT-5.4 的 H5 mapping ablation 表明，它能正确识别 `P₄+5Q₄=72141200`，但两次在对 1009 取余时算错。v1.1 因此把最终校验改为模 1000，保持组合问题不变，只移除长除法噪声。重跑结果：

| 模型 | target-only | with-source | with-lure（当时版本） | source gain |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.5 | 1/3 | 3/3 | 1/3 | +66.7pp |
| GPT-5.4 | 0/3 | 2/3 | 0/3 | +66.7pp |

GPT-5.4 的唯一 source 错误正好是只识别重命名同构、未检查 `H→G:4→9` 而输出基准 600，与当时的 copy-probe 一致。因此双模型的迁移方向在 v1.1 达成一致。

## v1.3：最终负控制

v1.2 曾将 lure 改为“允许内部环”，但它仍向模型提供了目标所需的未排环四次系数，属于有用的数值脚手架。v1.3 保留相同图、谱类、收敛条件与查询次数，但把所有边权折叠为 1；无权树谱四次系数为 1545，copy-probe 为 545。

v1.3 使用 v1.1 不变的 target/source 记录与新 lure 重跑后：

| 模型 | target-only | with-source | with-lure | transfer gain | structural selectivity |
| --- | ---: | ---: | ---: | ---: | ---: |
| GPT-5.5 | 1/3 | 3/3 | 1/3 | +66.7pp | +66.7pp |
| GPT-5.4 | 0/3 | 2/3 | 0/3 | +66.7pp | +66.7pp |

GPT-5.5 完成样本的平均输出为 target-only 13780、with-lure 12910、with-source 1018 tokens；GPT-5.4 分别为 3337、900、402 tokens。这说明 source 给出的是可复用的局部更新，而最终 lure 没有向 GPT-5.5 提供同等计算捷径。

## 首条正式 L0—L4 链

`data/v1/formal-p2-sensitivity-chain.yaml` 将 v1.3 seed 派生为五级、固定 source 的 P2 链，并在 `data/schema_cards/formal-p2-sensitivity-v1.yaml` 中预注册层级合约。

| level | 目标复杂度 | GPT-5.5 target | source | 最终 lure |
| --- | --- | ---: | ---: | ---: |
| L0 | 2 个非根点，直接枚举 | 1 | 1 | 1 |
| L1 | 4 点单环排除 | 1 | 1 | 1 |
| L2 | 6 点多项式树谱 | 1 | 1 | 0 |
| L3 | 8 点完全重命名同构 | 0 | 1 | 0 |
| L4 | 8 点重命名 + 单边扰动 | 0 | 1 | 1 |

这是单样本 sanity，不用于正式定级。它表明能力曲线已从 L0—L2 的 target-only 全对，过渡到 L3—L4 的 target-only 全错，而 source 在五级均正确。合并最终 lure 后，target/source/lure 分别为 3/5、5/5、3/5，初步 source gain 和 structural selectivity 均为 +40pp。

该链当前使用 `calibration` split；只有在更多样本和更多模型上确认各级间距后，才应冻结并派生隐藏 test 变体。
