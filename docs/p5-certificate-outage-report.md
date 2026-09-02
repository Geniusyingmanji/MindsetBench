# P5 规划证书：动作冻结反事实消融

## 构造

`data/v1/formal-p5-certificate-outages.yaml` 从 Formal35 的 L4 十六卡实例派生三个单动作冻结反事实。
冻结卡仍完整展示在表中，但不属于本次可执行动作集合；每题都必须重新报告六段最优/次优证书。

| case | 冻结影响 | 真值变化 |
| --- | --- | --- |
| `OUTAGE-K13` | 不影响最优，只删除一条 runner-up | `17/唯一/18×3 → 17/唯一/18×2` |
| `OUTAGE-K2` | 不影响最优，清空整个旧 runner-up 层 | `17/唯一/18×3 → 17/唯一/19×3` |
| `OUTAGE-K6` | 直接删除旧最优路径 | `17/唯一/18×3 → 18/唯一/19×3` |

固定 source 是一个五操作小型冻结示例：S5 冻结前成本 3 有两条 runner-up，冻结后只剩一条。lure
则给出目标十六卡系统在“全部卡可用”时的完整基线证书。三题都保留为 calibration/ablation，不并入
Formal35 的七条完整 L0—L4 链。

## 可执行验证

Verifier 从 source、target 和 lure 题面分别重建完整动作表，解析唯一 `冻结卡=...` 声明，再从有效动作
集合删除冻结卡。它检查 source 的冻结前后计数、目标六段证书、基线 lure 证书、六段差分位置、旧最优
路径是否仍可执行，以及路径分隔符和 lure 角色盲化。

独立 first-hit DFS 不调用 verifier 的一致代价搜索，复核得到：

- K13：`{17: 1, 18: 2}`；
- K2：`{17: 1, 19: 3}`；
- K6：`{18: 1, 19: 3}`。

严格校验、transfer audit 与三个 verifier 均为零错误、零警告；每题执行 22 项检查。

## GPT-5.6-sol 预筛

Matrix OpenAI-compatible 端点，12,288 输出 tokens，上述每格均只有一个样本。独立 target-only
首轮为 3/3 exact、18/18 parts、100% coverage，无截断。随后重新运行完整三条件配对：

| 条件 | exact | parts | 平均输出 tokens | 平均延迟 |
| --- | ---: | ---: | ---: | ---: |
| target-only | 3/3 | 18/18 | 5,082 | 93.2s |
| with-source | 2/3 | 13/18 | 5,676 | 95.8s |
| with-lure | 3/3 | 18/18 | 4,415 | 72.5s |

target-only 在两次独立运行中都是 3/3，说明显式给出冻结卡号后，这组三题对 GPT-5.6-sol 已形成
ceiling。with-source 唯一失败发生在 K13：模型完全漏掉不含 K13 的成本 17 路径，从 K7 分支开始，
输出 `18;非唯一;0;2;19;4`。这不是 source 答案的精确复制，三个条件的 copy-probe rate 都为 0；
单样本下既可能是类比锚定造成的负迁移，也可能是搜索方差，不能区分。

with-lure 三题全对，说明当前“全启用基线证书”并不是有效的有害控制。虽然它冻结语义不同，但它直接
提供了目标同标签的基线最优/runner-up 层，模型可以把它当作有用 scaffold 后再删除冻结路径。因此本轮
得到 exact transfer gain -33.3pp、part transfer gain -27.8pp 和负 structural selectivity，不能解释为
模型偏好错误结构；更合理的结论是 control 与 target 共享了过多可复用数值和路径信息。

## 决策

1. 三个显式冻结题保留为 verifier 回归和 counterfactual sanity，不作为主难度或正迁移证据。
2. 后续不再把同标签的完整基线证书当 lure；应路径解耦或重命名，使错误结构不能同时提供直接可用的
   搜索结果。
3. 下一版把冻结位置编码成操作属性谓词，并在一道题中联合回答多个独立策略；模型必须先做关系选择，
   再重算多个成本层。
4. 若联合题仍出现 ceiling，再加入未指明位置的效果编辑识别或 top-k 成本层摘要，并用至少三样本复核。

## 复现

```bash
.venv/bin/mb validate data/manifests/formal-p5-certificate-outages.json --strict-v1
.venv/bin/mb audit data/manifests/formal-p5-certificate-outages.json
.venv/bin/mb verify all --dataset data/manifests/formal-p5-certificate-outages.json
.venv/bin/pytest -q tests/test_formal_p5_certificate_outage.py
```

API 凭据只经环境变量或终端隐藏输入传入；实验 SQLite 位于 ignored 的 `artifacts/runs/`。
