# Humanities/Social-20 构造与校准报告

## 当前状态

`hss20` 已完成四条固定源 L0–L4 链，共 20 题。它们现定位为经过格式修复的
`calibration/sanity` 资产，而不是已达标的高难测试集：

| 链 | 范式 | 核心 mindset | L3/L4 目标 |
| --- | --- | --- | --- |
| HN | P4 | 默认规则、成对例外和局部优先关系更新 | 劳动申诉文书；公共档案先例 |
| HE | P7 | 引用谱系去重、攻击传播和独立性单位恢复 | 艺术品来源档案；匿名历史文书 |
| HA | P6 | 按因果角色映射并审计策略依赖边 | 外交编年；社会运动多文书 |
| HM | P8 | 区分选项删除、类型成本和实际成本承担者 | 公地会议纪要；联盟账册与密函 |

全部材料为虚构设定。20/20 题使用标签、集合或角色对应，不包含数值答案。8 个 L3/L4 已扩为
6–10 个答案部件，并加入近似关系子图、跨文书共同来源、选项恢复权或理由证书；四个 L4 都有局部关系变化、
确定性 lure 和与 gold 不同的 copy probe。但 GPT-5.6 的实测表明，这些增强仍未形成难度净空。

## 距离与领域配比

8 个 L3/L4 均跨文体、跨表征。方向预注册为：

| 链 | 源域 | 高等级目标域 | 方向 | 数量 |
| --- | --- | --- | --- | ---: |
| HN | 软件权限手册 | 劳动制度、公共档案 | technical→HSS | 2 |
| HE | 工程证据审查 | 艺术史、历史文书 | technical→HSS | 2 |
| HA | 山区公地治理 | 外交史、社会运动史 | HSS→HSS | 2 |
| HM | 跨港商会制度 | 公地治理、联盟制度史 | HSS→HSS | 2 |

因此高等级切片恰好一半为技术源到人文社科目标，一半为人文社科内部远迁移。全体 target 中只有 HN、HE
各自的 L0/L1 保留技术域，其余 16/20 属于公共治理、法律/劳动、传播、文化或历史分析。

## 可执行验证

当前检查结果：

- `hss20` strict validation：20 题，0 error，0 warning；
- schema cards：4 cards 对应 20 题，0 error；
- transfer-design audit：20 题，0 error，0 warning；
- executable verifier：20/20 PASS；
- 全仓测试：174 passed；
- 静态检查：通过。

验证器没有直接信任存储答案：四类题分别由有限优先规则、证据有向图、关系子图枚举和制度机制分类器
重算 gold；lure 使用独立的替代关系或替代机制复算。

## L4 的预注册照搬错误

| Case | 目标局部变化 | 机械照搬后果 |
| --- | --- | --- |
| HN/P4 | 法院解密令只推翻契约封存 | 多拒绝 `U5`；若过度泛化又会错放 `U8` |
| HE/P7 | 不同底本可能共享同一协调生产过程 | 把 `H1`、`H4` 错判为 `SUPPORTED` |
| HA/P6 | 压力组织反向控制治理节点 | 角色仍匹配，却漏报 `P-CONTROLS-G` |
| HM/P8 | 担保人垫付并全额返还保证金 | 把 `H1` 从 `POOLING_SIGNAL` 错判为 `SEPARATING_SIGNAL` |

## GPT-5.6 校准结果

两轮均只测试 8 个 L3/L4，每题每条件 3 样本：`target-only / with-source / with-lure`，每轮 72 次调用。
模型为 `gpt-5.6-sol`，每次最多 2,048 completion tokens；两轮均无截断。API 凭据只进入运行进程，
没有写入数据、配置或结果库。

第一轮暴露了题面与 grader 的契约错误，不能用于难度结论：

| 条件 | 整题 exact | 逐部件 | 诊断 |
| --- | ---: | ---: | --- |
| target-only | 8/24 | 53/114 | 多数语义答案正确，但缺少题面未要求的 `A=`、`R1=`、`FATAL=` 前缀 |
| with-source | 24/24 | 114/114 | source 的示例答案意外教会了隐藏格式 |
| with-lure | 17/24 | 101/114 | lure 也提供了同一格式脚手架 |

因此首轮表面的 `+66.7pp` source gain 主要是格式泄漏，不能解释为 mindset transfer。随后在数据模型中加入
独立的 `target.answer_format`，由统一 prompt builder 对所有条件注入占位格式；完整 gold 不进入 prompt view，
校验器也拒绝把多部件完整 gold 填入格式字段。

第二轮同时扩大了结构：P4 对 10 份卷宗报告结论和控制理由，P6 加入四边近似子图，P7/P8 各扩成六项跨文书判断。
结果仍全部达到天花板：

| 条件 | 整题 exact | 逐部件 | copy-probe | 平均输出 tokens | 平均延迟 |
| --- | ---: | ---: | ---: | ---: | ---: |
| target-only | 24/24 | 168/168 | 0/24 | 547.0 | 10.59s |
| with-source | 24/24 | 168/168 | 0/24 | 404.5 | 7.85s |
| with-lure | 24/24 | 168/168 | 0/24 | 428.9 | 8.63s |

P4/P6/P7/P8、L3/L4 的每个分层格子都是 100%。source 相对 target-only 少约 26.1% 输出 tokens、延迟低约
25.8%，但 lure 也呈现相似效率改善；在准确率无净空时，这只能视为上下文脚手架的效率迹象，不能视为正迁移。

## 当前结论与下一轮

这 20 题的数据结构、答案契约和 verifier 合格，但难度门不合格。实验证伪了两条路线：严格格式不一致制造的是
假地板，增加卷宗、答案部件和显式干扰关系仍会形成真天花板。`hss20` 继续留在 calibration/sanity，不能进入
hidden test，也不能用它报告 source gain。

下一轮不再直接扩写现有 L3/L4，而先做四个 latent-structure hard seed。构造遵循
[arXiv:2605.11258](https://arxiv.org/abs/2605.11258) 的对象映射与共享关系表示，同时反向应用 leakage removal：

1. target 只保留原始判决、档案、叙事或制度记录，不给整理后的规则、关系名或关键反转提示；
2. 从若干观测联合恢复潜在优先关系、来源家族、功能角色或成本/选项控制权，再回答反事实新实例；
3. L3/L4 只局部保留 source 关系，并加入必须适配的一删一增；lure 预注册为错用旧关系后的完整答案；
4. 每个 seed 先跑 target-only 三样本；达到 20%–60% 才运行全三条件，避免再次批量生产 sanity 题。

复现实验：

```bash
.venv/bin/mb run \
  --dataset data/manifests/hss20-hard.json \
  --database artifacts/runs/hss20-hard-gpt56sol-v2.sqlite \
  --experiment-id hss20-hard-gpt56sol-s3-v2 \
  --model gpt-5.6-sol \
  --endpoint https://matrixllm.alipay.com/v1/chat/completions \
  --conditions target-only with-source with-lure \
  --samples-per-item 3 \
  --max-output-tokens 2048

.venv/bin/mb report \
  --database artifacts/runs/hss20-hard-gpt56sol-v2.sqlite \
  --experiment-id hss20-hard-gpt56sol-s3-v2 \
  --calibration-gates \
  --min-samples 3 \
  --part-details
```

结果库在 `artifacts/` 下且默认不进入 Git；报告中的聚合数字来自可恢复 SQLite，而不是手工抄写单条回答。
