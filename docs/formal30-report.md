# Formal30 构造与预筛报告

## 范围

`data/manifests/formal30.json` 在原 formal25 的五条 L0—L4 链上新增一条 P5 潜在操作链，形成六个 schema、30 个 calibration cases：

- P2：谱系数灵敏度迁移；
- P3：线性因果路径与单边机制变化；
- P4：规则闭包与单规则消融；
- P5a：显式有状态操作规划；
- P5b：匿名仿射操作码本恢复、跨表征映射与关系编辑后重规划；
- P6：节点置换与关系词典联合对齐。

新增 P5b 链不是把显式操作表继续加长，而是引入三个相互独立的难点：从局部有歧义的输入输出观测恢复全局注入码本、识别位向量与集合对称差的同构、在一项隐藏操作变化后重算最低成本计划。

## L0—L4 梯度

| 等级 | 目标变化 | 可执行保证 |
| --- | --- | --- |
| L0 | 同域四操作，每条日志局部唯一 | 唯一码本；唯一三步最优，成本 8，runner-up 9 |
| L1 | 同域四操作，三条日志各有两个候选 | 局部规模 1/2/2/2，但全局一一匹配唯一；最优成本 7 |
| L2 | 跨到继电域，八操作、日志与卡名完整重命名 | 与 source 码本完整同构；最优成本 12，runner-up 13 |
| L3 | 九选八，隐藏地把一张卡从 F4 改为 F9 | F4 唯一未使用；旧计划落到错误终态，改版最优成本 7 |
| L4 | 位串改为点亮站位集合，“排列+异或”改为“取位+对称差”，保留单关系编辑并回答三问 | 逐状态验证 G1—G9 与 F1—F9 等价；三问唯一最优成本 7/11/11 |

L0—L2 的 lure 只翻转输出串与实际复合方向，L3—L4 的 lure 则冻结编辑前的旧码本。所有 lure/copy-probe 在真实规则下均可重放并确定性错失目标，不依赖无法执行或自由文本判断。

## Verifier 与测试

统一 verifier 同时支持两种题面解析：

1. 位串表示：`P(i1,…,i8)⊕mask`；
2. 集合表示：新站位取旧站位成员关系，再与翻转集合取对称差。

每题执行 16 类检查，包括题面结构解析、source/target 码本唯一性、局部候选规模、所有查询的唯一最低成本计划、runner-up 成本集合、lure 模型解、单关系差分、lure 在真实码本下的错误终态和存储答案一致性。测试还对九对 F/G 变换各枚举全部 256 个状态，并验证篡改 G9 翻转集合会被拒绝。

本轮静态门槛结果：

- formal30 严格校验：30 cases，0 errors，0 warnings；
- 完整链审计：六条链均覆盖 L0—L4；
- schema cards：6 cards 对 30 cases，0 errors；
- 新链：五题各 16 项 verifier 全部通过。

## GPT-5.5 快速预筛

端点为 Matrix OpenAI-compatible API。以下仍是单样本诊断，不能用于宣称达到 20%—60% target-only 接受窗，也不能估计稳定的 source gain。

| 实验 | 条件 | 上限 | finish | 输出 tokens | 延迟 | 诊断 |
| --- | --- | ---: | --- | ---: | ---: | --- |
| L3 target v1 | target-only | 16,384 | stop | 9,295 | 120.8s | 码本、成本和计划均正确，但答案行漏分号；严格格式失败，不算认知错误 |
| L3 paired v2 | target-only | 16,384 | length | 16,384 | 200.6s | 删失 |
| L3 paired v2 | with-source | 16,384 | stop | 6,854 | 104.4s | 正确采用 source 方法，但把 F9 手算错一位，误报日志矛盾和“无解” |
| L3 paired v2 | with-lure | 16,384 | stop | 9,592 | 142.7s | 码本正确，停在成本 11 的可达次优计划，漏掉成本 7 最优；非精确 copy 命中但属于搜索负迁移 |
| L4 v1 | target-only | 16,384 | length | 16,384 | 188.7s | 删失 |
| L4 paired v1 | with-source | 16,384 | length | 16,384 | 200.5s | 删失 |
| L4 paired v1 | with-lure | 16,384 | length | 16,384 | 244.3s | 删失 |
| L4 target 32K v2 | target-only | 32,768 | stop | 27,360 | 361.1s | 唯一码本和 Q1 正确；Q2/Q3 均给成本 14 的次优路径，真值为 11/11 |

32K 试次证明 L4 的 16K 失败不只是输出上限问题：额外预算让模型完成并正确跨越集合/位向量表示，也恢复了唯一代码本，但多查询最低成本搜索仍不完备。当前难度过高且推理成本大，适合作为 challenge calibration，不应直接进入正式 test。

L3 的两次 target-only 结果（一条语义正确但格式失败、一条删失）也显示单样本方差很大。with-source 在唯一有效 paired 试次中缩短了输出与延迟，却因局部位运算错误失分；因此目前没有正 source gain 的证据。

## 下一轮决策

1. 保留三问 L4 作为高预算 challenge 轨，不用截断 trial 计算准确率。
2. 增加 staged 版本：先单独判“候选集合 + 唯一码本”，再把已恢复码本作为固定输入判三个规划查询；分别报告 identification 与 planning 分数。
3. 为规划阶段增加逐查询可判 answer parts，避免 Q1 正确被 Q2/Q3 的错误完全淹没；总分仍保留严格全对指标。
4. staged 题通过完成率门槛后，再按至少三样本、至少两个能力档模型运行 target/source/lure，不把这轮单样本当作等级定标。

## 复现

```bash
.venv/bin/mb validate data/manifests/formal30.json --strict-v1
.venv/bin/mb validate-cards data/manifests/formal30-cards.json data/manifests/formal30.json
.venv/bin/mb audit data/manifests/formal30.json --require-complete-chains
.venv/bin/mb verify all --dataset data/manifests/formal30.json

.venv/bin/mb plan-run \
  --dataset data/manifests/formal-p5-latent-high.json \
  --conditions target-only with-source with-lure \
  --samples-per-item 3 \
  --max-output-tokens 16384
```

真实调用仍只从 `MINDSETBENCH_API_KEY` 环境变量读取凭据；SQLite 结果位于 ignored 的 `artifacts/runs/`，不进入 Git。
