# Formal35：有状态规划最优性证书链报告

## 范围与目标

`data/manifests/formal35.json` 在 formal30 的六条 L0—L4 链上新增
`stateful-planning-optimality-certificate-edit-v1`，形成七条完整链、35 个 calibration cases
和七张 schema card。新链不是继续增加潜在码本恢复的长度，而是把 P5 规划改写成可逐段判分的
最优性证书：

1. 最优成本；
2. 唯一最优有序路径；
3. 更低成本目标路径数；
4. 最优层目标路径数；
5. 首个次优成本；
6. 次优层目标路径数。

它专门测量模型能否区分“找到一条好路径”和“完整处理两个目标成本层”。第三段在一致证书中必为
0，本身不是主要难点；它的作用是暴露只报候选解却没有保持证书内部一致性的输出。主要难点位于完整的
有序路径计数、负前置/负目标、删除副作用，以及局部关系编辑后的整层重算。

## L0—L4 梯度

| 等级 | 状态空间变化 | 真值证书 | 预注册错误结构 |
| --- | --- | --- | --- |
| L0 | 三操作、两步依赖 | `2;A1>A2;0;1;3;1` | 删除前置后把 A2 当作成本 1 的独立置位 |
| L1 | 推进会清除终态资源，必须再恢复 | `4;B1>B2>B3;0;1;5;1` | 忽略清除后把 B2 当作成本 1 的直达操作 |
| L2 | 九操作、正负前置和正负终态 | `11;C2>C1>C3>C4>C5>C6>C7;0;1;13;1` | 独立加法覆盖得到成本 3/4 两层 |
| L3 | 十状态、十六操作同时重命名和乱序 | `15;K7>K2>K10>K4>K9>K1>K6>K3;0;1;16;3` | 相同卡表上的加法覆盖证书 |
| L4 | 仅把 K3 的登记效果从 v 改为 p | `17;K8>K10>K4>K9>K1>K6;0;1;18;3` | 冻结编辑前 K3 效果并沿用旧 15/16 证书 |

L3 与 source 是逐操作同构；L4 则只破坏一个效果关系。旧 L3 最优路径在新版中可以执行，但最后缺少
终态所需的 v，因此不能靠换名复制 source 证书。L4 的最优路径、最优成本、runner-up 成本和 runner-up
多重性都需要在新版状态空间重新计算。

## 可执行保证

Verifier 从题面重新解析初态、正负终态及全部操作，而不是直接信任代码内真值。真实模型在
`状态 × 已用操作集合 × 完整有序路径` 上做正成本一致代价枚举，路径首次满足完整终态即停止；为保留
多重性，等成本但顺序不同的路径不能被单纯按状态合并。错误模型则独立枚举 add-only 操作子集。

每题覆盖以下硬检查：题面与形式化实例一致、source 证书可机器解析、目标最优路径唯一、首个次优成本及
多重性正确、lure 证书可独立求得、lure 最优路径在真实系统中失败、copy probe 与真值不同。L3 另检查
完整操作/特征同构，L4 另检查仅 K3 发生效果变化以及旧计划确实失效。

独立测试没有复用 verifier 的 UCS，而是用 first-hit DFS 直接数路径，得到目标成本层：

- L0：`{2: 1, 3: 1}`；
- L1：`{4: 1, 5: 1}`；
- L2：`{11: 1, 13: 1}`；
- L3：`{15: 1, 16: 3}`；
- L4：`{17: 1, 18: 3}`。

add-only 控制也用独立组合枚举复核。所有题面显式规定路径内部使用 `>`，避免把语义正确但分隔符不同的
输出误判为推理失败。参考题在渲染后不得出现“错误”“真实”“目标题”“新版”等标签，防止 lure 条件
泄露实验角色。

## GPT-5.6-sol 单样本预筛

调用 Matrix OpenAI-compatible 端点，输出上限为 16,384 tokens。API 凭据只通过环境变量或终端隐藏输入
传入，SQLite 结果位于 ignored 的 `artifacts/runs/`。所有结果都只有每格一个样本，只用于发现题面缺陷和
定位难度，不能估计稳定迁移效应。

### 输出契约修复

首轮 target-only 的五题数值、路径及计数在语义上全部正确，但模型统一用逗号连接路径，严格 exact 为
0/5。由于题面当时没有规定路径内部分隔符，这属于 benchmark contract 缺陷而不是模型失败。加入
“路径内部只能用 `>`，不能用逗号”并由 verifier/test 强制后，重新运行得到：

| 等级 | exact | parts | 输出诊断 |
| --- | ---: | ---: | --- |
| L0 | 1 | 6/6 | 全对 |
| L1 | 1 | 6/6 | 全对 |
| L2 | 1 | 6/6 | 全对 |
| L3 | 1 | 6/6 | 全对 |
| L4 | 0 | 5/6 | 最优成本 17、最优路径及 runner-up 成本 18 均正确，只把次优路径数 3 报为 2 |

修复后总计 exact 4/5（80%），逐段 29/30（96.7%），coverage 100%，无截断。L0—L3 对
GPT-5.6-sol 已接近 sanity ceiling；L4 的 runner-up 多重性构成当前边界。

### 盲化 paired 对照

早期 paired 运行中，L4 lure 解答直接提及“真实新版”关系，造成条件泄露；该轮只保留为审计记录，完全
排除在迁移与 selectivity 结论之外。修复并加入渲染级无泄露测试后，仅对 L3/L4 运行三条件：

| 条件 | exact | parts | 平均输出 tokens | 平均延迟 |
| --- | ---: | ---: | ---: | ---: |
| target-only | 1/2 | 11/12 | 4,794 | 91.8s |
| with-source | 1/2 | 11/12 | 3,383 | 56.7s |
| with-lure | 1/2 | 7/12 | 4,411 | 76.7s |

L3 三个条件均为 6/6。L4 的 target-only 与 with-source 输出完全相同：都找到正确的成本 17 唯一路径，
并把成本 18 的路径数报成 2；因此 exact transfer gain 和 part transfer gain 都为 0。source 条件的两题
平均输出 tokens 比 target-only 少 29.4%，平均延迟少 38.3%，但样本太少且 L4 本身反而更慢，不能把
效率差异解释为稳定迁移收益。

盲化 lure 下，L4 输出 `18;非唯一;0;2;19;6`，只有“更低成本目标路径数为 0”这一段正确，从
target-only 的 5/6 降到 1/6。整体 exact structural selectivity 仍为 0，因为 L4 两边都没有全对；逐段
structural selectivity 为 +33.3pp。三个条件的 exact copy-probe rate 都为 0，所以这更像错误结构改变了
搜索与计数，而不是逐字复制预注册 lure 答案。

## 当前结论与下一轮

1. 证书化成功把原来“全错或全对”的规划题拆成可定位信号；当前稳定暴露的是 runner-up 路径计数遗漏。
2. L0—L3 对当前强模型偏易，应保留为解析、格式和迁移同构 sanity checks，不用于主难度估计。
3. L4 已越过 exact ceiling，但单样本中 source 没有提升准确率；不能宣称正迁移。
4. 盲化后的错误结构会显著伤害 L4 逐段表现，说明 lure 对结构选择有诊断价值，但必须用多样本复现。
5. 下一轮将保持可执行真值，扩展多个同构 L4 变体，并把查询改为指定 runner-up 分支、禁用一项操作后的
   反事实证书或 top-k 成本层摘要，减少固定为 0 的低成本计数字段所占权重；随后按至少三样本、两个能力档
   模型做正式校准。

## 复现

```bash
.venv/bin/mb validate data/v1/formal-p5-certificate-chain.yaml --strict-v1
.venv/bin/mb validate-cards \
  data/schema_cards/formal-p5-certificate-v1.yaml \
  data/v1/formal-p5-certificate-chain.yaml
.venv/bin/mb audit data/v1/formal-p5-certificate-chain.yaml --require-complete-chains
.venv/bin/mb verify all --dataset data/v1/formal-p5-certificate-chain.yaml

.venv/bin/mb validate data/manifests/formal35.json --strict-v1
.venv/bin/mb validate-cards data/manifests/formal35-cards.json data/manifests/formal35.json
.venv/bin/mb audit data/manifests/formal35.json --require-complete-chains
.venv/bin/mb verify all --dataset data/manifests/formal35.json
```
