# 基于 AR 的高难迁移题构造协议

本协议将 [Shen, Druckmann & Zou (2026), arXiv:2605.11258](https://arxiv.org/abs/2605.11258) 的 analogical-reasoning 管线改造成 MindsetBench 的封闭式、可执行验证题目生产流程。

## 为什么首批 20 题不合格

首批题虽然满足数据 schema 和 L0—L4 的形式要求，却把关键结构直接暴露给模型：P3 给出完整 DAG，P4 明示规则优先级，P6 直接指出“门控职责”，P2 只有极小搜索空间。模型在 target-only 条件下无需识别或迁移 source schema，因此 100% 正确不能测量迁移。

这些题只保留为 runner、grader 和 verifier 的 calibration/sanity 数据，不计入正式扩题数量。

## 从论文借用的核心方法

论文把 analogy 表示成对象映射与共享关系两部分，并允许目标类比只保持源问题关系的一个子集。其工作流分为：

1. Extraction：从原问题抽取功能对象、对象间关系，再生成跨域类比。
2. Search：沿显式对象映射和共享关系，在远域寻找可迁移的真实方法。
3. Curation：按大量 base-domain × target-domain 组合检索真实论文，并通过文献 API 核验来源。
4. Leakage removal：把目标问题重写成只陈述目标，删除来源领域、机制和方法提示。
5. Quality audit：检查结构深度、领域距离、可用性、新颖性、意外性和非显然性。

论文研究的是开放式科学解法生成，不直接提供封闭问答难度控制。因此 MindsetBench 只借用其“发现—抽取—检索—去泄漏—审计”构造管线，判分仍使用确定性 verifier。

## MindsetBench 的反向编译流程

### 1. 从真实跨域方法出发

先寻找一个确实发生过的方法迁移，而不是先写一道带标签的简单题。候选必须记录：

- 原始论文和可核验来源；
- base/target domain；
- 被迁移的具体机制、算法或关系结构；
- 是否为常见教材例子；
- 属于 conceptual motivation、methodological adaptation 或 deep structural transfer。

正式 L3/L4 优先选择非著名的 methodological adaptation 或 deep structural transfer。

### 2. 抽取结构，不映射属性

为 base 与 target 分别建立：

- `objects`：对象及其功能角色；
- `relations`：至少 4 条有方向或有参数的关系；
- `attributes`：只属于表面的属性，禁止作为映射依据；
- `mapping`：对象到对象的功能映射；
- `preserved_relations` 与 `broken_relations`。

候选若只靠相似名词即可发现，直接淘汰。

### 3. 将真实方法编译成封闭任务

把迁移后的方法实例化成一个具有唯一输出的合成实例：数值、最优方案、完整调整集、违规集合、关系映射或可达性结论。参数由 verifier 反向采样，必须同时满足：

- 真值唯一；
- copy-probe 与真值不同；
- lure 解法能稳定产生另一个确定答案；
- 暴力穷举或独立算法可复算；
- 不能通过答案标签分布或词面线索猜中。

### 4. 对目标题执行去泄漏重写

目标题只保留完成任务所需的原始事实和目标，删除：

- base domain 的术语；
- schema、算法、定理和机制名称；
- “这是一个因果图/优先级规则/角色映射”等任务类型提示；
- 已整理好的中间表示；
- “请注意例外/不要控制中介”等解题提示。

需要先从自然叙述或原始表格恢复形式结构，才算有效目标题。

### 5. 用关系保持度生成 L0—L4

| 等级 | 构造方式 |
| --- | --- |
| L0 | 同域、同表示、同算法，只换参数；作为能力上界锚点 |
| L1 | 同域但隐藏中间表示，需要先恢复对象与关系 |
| L2 | 跨域完整同构，全部核心关系保持，source 算子可逐步复用 |
| L3 | 只保持核心关系子集，加入一个会使直接照搬失败的新约束或关系 |
| L4 | 领域遥远且模型/算法表面不同，只能通过高阶机制重新实例化；不得退化为标签分类 |

L3/L4 的难度来自“哪些关系应保留、哪些必须改写”，而不是单纯增加文本长度。

### 6. 反向构造 lure

lure 保持目标领域、对象名和多数属性，但替换最关键的一条关系。提示模板不得告知模型哪一道是 lure。L3/L4 的 lure 答案应尽量等于 copy-probe，以形成可测的负迁移路径。

## 进入正式题库的硬门槛

每个候选先单独进行 target-only 预筛，再运行配对条件：

| 指标 | 接受范围 |
| --- | --- |
| frontier model target-only | 20%—60% |
| target-only ≥80% | 降为 sanity 或重写 |
| with-source − target-only | 至少 +15 个百分点，或在多模型上方向一致 |
| with-lure | 应低于 with-source，且允许命中预注册 copy-probe |
| verifier | 两种独立实现一致，或穷举与优化算法一致 |
| 泄漏审计 | 不出现 schema/method/base-domain 提示词 |
| 映射审计 | 至少 4 个功能对象、4 条核心关系；L3/L4 明示 broken relations |

`finish_reason=length` 的试次在难度校准中记为 censored，而不是直接解释为推理错误。主实验应预先固定足够的输出预算；若要研究 source 是否降低推理成本，则把完成率、输出 tokens 和延迟作为独立效率指标报告。

正式校准使用至少 3 个样本和至少 2 个能力档模型；单模型单样本只用于快速淘汰，不能用于确定等级。

## 下一批 20 题的生产顺序

先为 P2、P3、P4、P6 各制作一个 L3 hard seed。四个 seed 通过 target-only 净空与 with-source 增益门槛后，再围绕每个 seed 派生 L0、L1、L2、L4，最终形成四条 5 题链。这样避免再次批量生产 20 道结构正确但没有测量净空的题。

## 2026-09-01 执行进度

- P2 已经历 GF(2)、联合图映射、布尔 Möbius 反演、普通矩阵树计数和谱系数提取等多轮过易变异。
- `HARD-P2-L4-05` v1.3 在 GPT-5.5 上 target/source/lure=1/3、3/3、1/3，在 GPT-5.4 上为 0/3、2/3、0/3；两模型的 source gain 与 structural selectivity 都为 +66.7pp。
- 已由该 seed 产生 `formal-p2-sensitivity-chain.yaml` 的完整 L0—L4 链，但仍位于 calibration split。
- P3 已扩展为线性 SCM 响应路径和与单边机制灵敏度链；source 提供全局响应向量，L4 改变一条结构系数。
- P4 已扩展为最小不动点规则闭包与单规则消融链；source 提供事实剖面闭包和消融差分，L4 停用一条中间派生规则。
- P6 已扩展为节点置换与关系词典联合对齐链；source 提供最优映射、一分边际和 runner-up，L4 用一删一增交换最优性。
- P5 已扩展为带正负前置、置位/清除副作用和成本的有状态操作规划链；L3/L4 经三轮迭代扩为 10 状态、16 操作、多个一分 runner-up，并把目标从紧凑表去脚手架为操作卡叙述。
- 2026-09-02 使用新 token 完成 GPT-5.5 单样本预筛：P3/P4/P6 为 6/6，P5 去脚手架版本为 2/2，均高于正式接受窗；P5 的平均输出 5826 tokens、延迟 81 秒，显示成本上升但准确率仍天花板。
- 当前共有五条 L0—L4 链、25 题，全部仍是 `calibration`。下一轮应引入潜在操作语义推断、条件效果或部分可观测性，而不是继续只增加显式状态表规模。详见 `docs/formal25-report.md`。
- 已实现首个 P5 潜在操作 L4 seed：从逐条有歧义的日志联合恢复匿名 GF(2) 仿射操作，再适配一项隐藏变换变化并求三个唯一最短计划。GPT-5.5 三查询 target-only 首个有效试次失败；with-source 与 with-lure 均在 16,384 输出 tokens 处删失，暂不能估计迁移增益。详见 `docs/p5-latent-seed-report.md`。
