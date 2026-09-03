# 远域主动学习任务：首轮构造与校准

## 目标

这一轮不再把“远域”理解为给同一组符号换名词。source 仍提供 P4 规范优先、P6 功能关系、P7 证据谱系、
P8 激励机制四类 mindset，但 target 同时改变：

1. 领域与文体：代码手册或工程报告迁移到残卷、舞谱、广播剧、木偶戏、装置艺术、口传史和外交礼物；
2. 任务动作：从直接分类改成“下一步查什么”或“依据第一次结果再查什么”；
3. 优化对象：查询服务于最终行动或标签，而不是完整识别潜在世界；
4. 负迁移：每题都有一个可执行的表面捷径模型，它会改变最优查询或允许错误提前停止。

这对应 active learning 的核心：学习者不是被动解完所有候选，而是在预算内选择最能降低任务相关不确定性的观测。

## 两层任务

| 层 | 数量 | 目标输出 | 领域例子 | 可执行约束 |
| --- | ---: | --- | --- | --- |
| 单步主动查询 | 4 | 一个查询及所有观测分支的结论 | 修院残卷、舞谱档案、广播剧、海港铭文 | 最小化最坏结论歧义，再最小化剩余版本空间 |
| 两阶段条件策略 | 4 | 首查、按首个回复选择的次查、全部叶结论 | 木偶戏、装置艺术、口传史、外交礼物 | 两步内决策充分；最坏成本、平均成本、叶规模依次最小 |

单步题的正确结构模型都唯一选择 `Q3`，对应表面捷径都唯一选择 `Q2`。两阶段题中，正确模型的两个首查
分支必须采用不同的第二查询；P6、P7 的表面捷径还会让一个分支错误地提前停止。gold、lure 和 copy probe
均由同一底层世界集合分别重算，而非手写答案差。

## 实现

- `active_query.py` 提供不可变的潜在世界、查询评分、决策充分分支和规范化答案编码；
- 同一模块提供深度二的成本敏感策略搜索，支持分支提前停止，并返回所有并列最优策略；
- 四类 verifier 先用既有规范、谱系、关系和机制求解器计算每个潜在世界的结论，再规划查询；
- 数据审计要求 L4 broken relation、适配说明、非泄漏答案格式、完整 lure/copy probe；
- 结果库位于 `artifacts/runs/`，不进入 Git，也不保存 API 凭据。

## GPT-5.6-sol 预筛

两层各只跑 `target-only`、每题 3 样本。按预注册难度门，只有冷启动出现净空后才值得运行
`with-source/with-lure`；因此本轮没有把无净空条件扩成额外调用。

| 数据 | 调用 | 整题 exact | 逐部件 | 截断 | 平均输出 tokens | 平均延迟 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 单步主动查询 4 | 12 | 12/12 | 48/48 | 0 | 688.8 | 15.17s |
| 两阶段条件策略 4 | 12 | 12/12 | 84/84 | 0 | 2866.7 | 55.47s |

四个范式各自都是 3/3。copy-probe 命中率为 0，说明模型没有采用预注册的简单表面捷径；但准确率仍是
100%，所以这八题只能作为 active-learning calibration/sanity，不能用于估计 source transfer gain。

两阶段题让平均输出增长约 4.2 倍、平均延迟增长约 3.7 倍，却没有降低 exact accuracy。这表明继续增加显式
候选、回复矩阵和策略树深度，主要增加搜索计算量，不会自然产生 mindset 联想难度。

## 下一轮难度方向

下一批不从这八题机械扩写到 20，而改成“查询生成/交互”种子：

1. 不给完整的候选×查询回复矩阵；查询以采访、档案申请、制度干预或反事实案例的自然语言操作定义，模型需自行
   推导各潜在解释对查询的预测；
2. 将 source mindset 只作为结构先验，target 给若干异质的历史记录和局部示例，要求恢复哪些差异会改变最终行动；
3. runner 增加真正的多轮 episode：隐藏世界响应第一次查询，模型据观测选择第二查询并提交最终判断；
4. 同时报决策正确率、查询成本、相对 oracle 的 regret、无效查询率和表面捷径命中率；
5. 仍执行 4-seed 闸门：GPT-5.6 target-only 三样本落在 20%–60% 后，才按 4 范式 × 5 任务形式扩到 20。

这种设计才能区分三件事：模型是否识别可迁移 mindset、是否知道哪个未知量对决策关键、以及是否会主动获取该信息。

## 复现

```bash
.venv/bin/mb validate data/manifests/hss-active8.json --strict-v1
.venv/bin/mb audit data/manifests/hss-active8.json
.venv/bin/mb verify all --dataset data/manifests/hss-active8.json

.venv/bin/mb run \
  --dataset data/manifests/hss-active-query4.json \
  --database artifacts/runs/hss-active-query4-gpt56sol.sqlite \
  --experiment-id hss-active-query4-gpt56sol-target-s3-v1 \
  --model gpt-5.6-sol \
  --endpoint https://matrixllm.alipay.com/v1/chat/completions \
  --conditions target-only --samples-per-item 3 --max-output-tokens 2048

.venv/bin/mb run \
  --dataset data/manifests/hss-adaptive-policy4.json \
  --database artifacts/runs/hss-adaptive-policy4-gpt56sol.sqlite \
  --experiment-id hss-adaptive-policy4-gpt56sol-target-s3-v1 \
  --model gpt-5.6-sol \
  --endpoint https://matrixllm.alipay.com/v1/chat/completions \
  --conditions target-only --samples-per-item 3 --max-output-tokens 4096
```

运行时 API key 只通过环境变量或终端隐藏输入传入。
