# Humanities/Social-20 构造与校准报告

## 当前状态

`hss20` 已完成四条固定源 L0–L4 链，共 20 题：

| 链 | 范式 | 核心 mindset | L3/L4 目标 |
| --- | --- | --- | --- |
| HN | P4 | 默认规则、成对例外和局部优先关系更新 | 劳动申诉文书；公共档案先例 |
| HE | P7 | 引用谱系去重、攻击传播和独立性单位恢复 | 艺术品来源档案；匿名历史文书 |
| HA | P6 | 按因果角色映射并审计策略依赖边 | 外交编年；社会运动多文书 |
| HM | P8 | 区分选项删除、类型成本和实际成本承担者 | 公地会议纪要；联盟账册与密函 |

全部材料为虚构设定。20/20 题使用标签、集合或角色对应，不包含数值答案。四个 L4 都有局部关系变化、
确定性 lure 和与 gold 不同的 copy probe。

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
- 全仓测试：171 passed；
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

## 模型校准计划

模型结果尚未产生：当前进程没有配置 `MINDSETBENCH_API_KEY`，因此没有把聊天记录中的凭据复制进命令、
配置或仓库。现阶段只能确认程序真值和评测矩阵可运行，不能声称题目已达到目标难度。

首轮只测试 8 个 L3/L4，每题每条件 3 样本：`target-only / with-source / with-lure`，合计 72 次调用；
P4/P6/P7/P8 各 18 次，L3/L4 各 36 次。最大完成 token 预算为 147,456。

安全配置环境变量后可运行：

```bash
.venv/bin/mb run \
  --dataset data/manifests/hss20-hard.json \
  --database artifacts/runs/hss20-hard-gpt56sol.sqlite \
  --experiment-id hss20-hard-gpt56sol-s3-v1 \
  --model gpt-5.6-sol \
  --endpoint https://matrixllm.alipay.com/v1/chat/completions \
  --conditions target-only with-source with-lure \
  --samples-per-item 3 \
  --max-output-tokens 2048

.venv/bin/mb report \
  --database artifacts/runs/hss20-hard-gpt56sol.sqlite \
  --experiment-id hss20-hard-gpt56sol-s3-v1 \
  --calibration-gates \
  --min-samples 3 \
  --part-details
```

首轮重点看 target-only 是否落入 20%–60%、with-source 是否改善高等级 exact/part accuracy，以及
with-lure 是否提高预注册 copy-probe 命中率。source gain 无论正负都保留并报告。
