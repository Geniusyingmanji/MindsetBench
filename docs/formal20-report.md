# 正式扩展候选 20 题：构造与校准状态

日期：2026-09-01。这里的“正式”表示题目已按高难构造协议生成并通过可执行真值验证；在多样本、多模型校准完成前，四条链仍全部使用 `calibration` split，尚未冻结为隐藏测试集。

## 题目组成

| 范式 | 固定 source 提供的可迁移证书 | L3 | L4 broken relation | 负控制 |
| --- | --- | --- | --- | --- |
| P2 | 带类型有向树谱 `P(x)` 与单边灵敏度 `Q(x)` | 八节点完全重命名 | 一条边权 4→9 | 同拓扑的无权树谱 |
| P3 | 线性 do-响应向量与单边上下游灵敏度 | 十节点 SCM 完全重命名 | 一条机制系数 5→9 | 同拓扑的无权路径数 |
| P4 | 十二事实剖面的闭包违规集与规则消融差分 | 谓词重命名、记录置换、目标权重化 | 一条中间派生规则停用 | 只读初始事实的一轮规则 |
| P6 | 联合图对齐的最优解、一分边际和 runner-up | 对整个双图对齐实例作元级重命名 | 一删一增使 runner-up 成为新最优 | 首次出现顺序固定错误词典 |

对应数据：

- `data/v1/formal-p2-sensitivity-chain.yaml`
- `data/v1/formal-p3-causal-chain.yaml`
- `data/v1/formal-p4-closure-chain.yaml`
- `data/v1/formal-p6-alignment-chain.yaml`

每个文件含固定 source 的 L0—L4 五题，共 20 题。P3、P4、P6 是本轮新增的 15 题；旧 `expansion20.yaml` 仍只作为偏易的 sanity 数据，不与这批候选混合。

为避免复制题目，聚合运行使用 JSON bundle：`formal20.json` 加载全部 20 题，`formal-new15.json` 加载三条新链，`formal-new-high.json` 只加载待预筛的六道 L3/L4；`formal20-cards.json` 聚合四张 schema card。

## 难度递进不是文本长度递进

三条新链都保持同一个测量结构：

1. L0—L1 用极小实例验证被测模型是否理解基本算子。
2. L2 引入噪声、旁路、混杂叙述或联合搜索，要求恢复中间结构。
3. L3 对 source 的完整求解对象作跨域重命名或顺序置换，但保留可迁移证书。
4. L4 在 L3 上只改变一条决定性关系；直接复制 source baseline 会失败，识别局部编辑后可低成本更新。
5. lure 保留目标对象和大部分表面结构，但破坏递归、权重或关系词典等关键语义，且答案与 copy-probe 预注册一致。

## 静态质量门

截至本报告生成时：

- 四条链均通过 `strict-v1`，无 error/warning；
- 四张 schema card 均完整覆盖 L0—L4；
- 20 个 case id 唯一，四个范式各五题，全部仍为 `calibration`；
- P2 使用穷举与多项式行列式；P3 使用拓扑动态规划与显式路径枚举；P4 使用最小不动点引擎与独立一轮求值器；P6 穷举节点排列与关系词典的直积空间；
- `mb audit --require-complete-chains` 另检查 copy-probe/lure 一致性、L3+ 至少四对象四关系、L4 broken relation 与适配要求；
- P6 高级 lure 额外加入三条共同噪声边：不改变正确映射的 14/13 分边际，却使错误词典下的节点解也发生偏移，L3/L4 分别只与目标重合 1/5、2/5 个节点；
- P3 边表、P4 记录表和 P6 双侧三元组均与 source 独立排序；高级 verifier 会反向解析题面并比对求解器输入，故错系数、错权重、漏边或误写有效规则都会失败；
- 全仓测试为 78 项，ruff 与 `git diff --check` 通过；永久 provider 4xx 不再重试或打印 traceback，partial trials 会保留并显式报告。

## 模型校准状态

P2 已完成此前报告中的 GPT-5.5/GPT-5.4 多样本校准。P3/P4/P6 在 2026-09-01 启动 GPT-5.5 target-only 预筛时，Matrix 端点返回 `access_forbidden`，明确说明所给 token 已禁用。runner 数据库中该实验为 0 trial；因此：

- 没有把服务错误记为模型答错；
- 没有 P3/P4/P6 的新模型准确率可报告；
- 不能据静态复杂度宣布三条新链已经达到 20%—60% target-only 门槛；
- 获得新 token 后应从 target-only 单样本预筛恢复，再只对 L3/L4 有净空的链运行三样本 source/lure 配对。

建议用六道高级题统一恢复预筛（密钥只放环境变量）：

```bash
export MINDSETBENCH_API_KEY='...'

# 先核对请求矩阵；三条件×三样本共 54 trials，不调用 API
.venv/bin/mb plan-run \
  --dataset data/manifests/formal-new-high.json \
  --samples-per-item 3 \
  --max-output-tokens 8192

.venv/bin/mb run \
  --dataset data/manifests/formal-new-high.json \
  --database artifacts/runs/formal-new-high-gpt55.sqlite \
  --experiment-id formal-new-high-gpt55-target-v1 \
  --model gpt-5.5 \
  --endpoint https://matrixllm.alipay.com/v1/chat/completions \
  --conditions target-only \
  --samples-per-item 1 \
  --max-output-tokens 8192
```

预筛后用新的 experiment id、三条件和 `--samples-per-item 3` 配对重跑。结果可重复分析而无需再次请求模型：

```bash
.venv/bin/mb report \
  --database artifacts/runs/formal-new-high-gpt55.sqlite \
  --experiment-id formal-new-high-gpt55-paired-v1 \
  --calibration-gates \
  --min-samples 3
```

报告会按范式检查每题每条件覆盖率、20%—60% target-only window、至少 +15pp source gain、正 structural selectivity、完成率，以及 source/lure 分条件 copy-probe 命中率和配对分歧方向。
