# P5 潜在仿射操作 hard seed 报告

## 目标

`HARD-P5-LATENT-L4-01` 不再把操作语义直接写在卡片上，而要求模型先从逐条有歧义的输入输出日志中恢复全局一一对应的匿名操作码本，再在“八位状态 × 已用卡集合”中求三个唯一最低成本计划。target 只改变一张卡的隐藏仿射变换；直接复制 source 的程序重命名会在三个查询上全部失败。

该题目前是 `calibration` hard seed，不计入正式 test。它用于验证下一轮 P5 L0—L4 链的难度方向：难度来自潜在操作辨识、broken relation 适配与精确规划的组合，而不是继续增加显式状态表长度。

## 可执行真值

- source 八张卡与 F1—F8 的全局代码本唯一；唯一最优计划成本为 12，runner-up 为 13。
- target 从九个候选中为八张卡恢复唯一注入代码本，其中 F4 未使用、`K7=F9`。
- target 三问的唯一最优成本依次为 7、11、11；次优成本依次为 9、12、12。
- 按旧码本复制的三条计划成本为 12、14、10，在真实 target 下分别落到 `11010100`、`01110001`、`01011111`，均未到达目标。
- verifier 联合检查解析、候选集合、码本唯一性、最短路唯一性、runner-up 间隔、单关系变化、copy-probe 错误终态和存储答案，共 19 项断言。

## GPT-5.5 单样本预筛

以下仅用于快速诊断，不满足“至少三个样本、至少两个能力档模型”的正式校准要求。`finish_reason=length` 统一记作删失，不计为有效答错。

| 版本 | 条件 | 输出上限 | 结果 | 输出 tokens | 延迟 | 诊断 |
| --- | --- | ---: | --- | ---: | ---: | --- |
| target v1，单查询 | target-only | 8,192 | 删失 | 8,192 | 99.5s | 到达长度上限，无答案行 |
| target v2，单查询 | target-only | 16,384 | 无效格式 | 9,298 | 117.1s | 推理结论正确，但没有按预注册分隔格式输出 |
| target v3，单查询 | target-only | 16,384 | 正确 | 10,361 | 126.5s | 修正输出约束后的有效试次 |
| target v4，三查询 | target-only | 16,384 | 错误 | 5,266 | 73.9s | 手算 F9 时发生位运算错误，误判为无解；非格式问题 |
| lure v1，三查询 | with-lure | 16,384 | 删失 | 16,384 | 223.9s | 到达长度上限，无答案行 |
| source v2，三查询 | with-source | 16,384 | 删失 | 16,384 | 246.5s | source 已缩为单查询，仍到达长度上限 |

当前最有信息量的有效结果是三查询 target-only 的一次真实推理失败，说明新构造已摆脱旧 P5 显式规划题的单样本天花板。但 paired 条件均被长度截断，尚不能估计 source gain 或 structural selectivity，也不能据此声称命中 20%—60% 接受窗。

## API 与 runner 诊断

2026-09-02 使用新的 Matrix 凭据时，请求得到服务端 request ID 并完整返回 provider 元数据，说明凭据与网络链路可用。最新 with-source 请求输入 1,443 tokens，约 246.5 秒后因 16,384 输出 token 上限结束；这不是 401/403 认证错误或客户端读超时。

本轮同时补强 runner：

- `ExperimentConfig` 新增持久化的 `request_timeout_seconds`，CLI 可显式控制单次请求读超时；
- 旧 SQLite 中没有该字段的配置会先按当前 schema 补默认值，再做续跑一致性比较；
- provider 将直接抛出的 `TimeoutError` 与 `URLError` 一并包装成可重试的 `ProviderError`；
- 对应兼容性、参数转发和异常包装均有回归测试。

## 复现

结构和答案验证不需要模型凭据：

```bash
.venv/bin/mb validate data/v1/p5-latent-seeds.yaml --strict-v1
.venv/bin/mb audit data/v1/p5-latent-seeds.yaml
.venv/bin/mb verify all --dataset data/manifests/p5-latent-seed.json
```

真实模型调用应只通过环境变量读取凭据，且为每次改变题面或提示的实验使用新的 `experiment-id`：

```bash
export MINDSETBENCH_API_KEY='...'
.venv/bin/mb run \
  --dataset data/manifests/p5-latent-seed.json \
  --database artifacts/runs/p5-latent-gpt55.sqlite \
  --experiment-id p5-latent-gpt55-target-v5 \
  --model gpt-5.5 \
  --endpoint https://matrixllm.alipay.com/v1/chat/completions \
  --conditions target-only \
  --samples-per-item 3 \
  --max-output-tokens 16384 \
  --request-timeout-seconds 300 \
  --max-retries 0
```

下一步不应立刻扩大样本量。先压缩 paired prompt 的非必要重复、要求模型用候选集合与搜索表的紧凑表示作答，并确认这种改写不泄漏目标码本；paired 条件获得可完成试次后，再扩为完整 L0—L4 链并进行多模型三样本校准。
