# P5 属性谓词联合证书报告

## 动机与构造

三个显式动作冻结变体对 GPT-5.6-sol 形成 3/3 ceiling，因此
`FORMAL-P5-CERT-POLICY-JOINT-01` 同时增加两个维度：

1. 冻结位置不再直接给卡号，而由操作费用、前置、置位、清除与正负目标之间的集合谓词确定；
2. α、β、γ 三个策略在同一题中独立回到全启用基线，分别冻结唯一匹配卡并输出完整证书。

三个可执行谓词唯一匹配 K13、K2、K6。每组答案由“匹配卡号 + 六段最优/次优证书”构成，总计
21 段。三种冻结影响依次为：只减少旧 runner-up 多重性、清空整个旧 runner-up 层、直接击穿旧最优
路径。

source 只展示一个五操作、七段输出的属性谓词冻结示例。solved lure 使用完全不同的 R 卡、成本和路径，
并采用“谓词只产生审计标签、不改变动作可用性”的结构。oracle/false mindset 进一步移除所有源路径和
数值，只保留相反的程序性规则。

## 可执行保证

Verifier 从题面重建完整十六卡实例，对三个关系谓词逐卡执行并证明各自只有一个匹配；随后创建三个独立
十五卡实例，分别枚举到第二个非空目标成本层。它还检查：

- source 谓词唯一匹配 S5，冻结后证书为 `S5;2;S1>S2;0;1;3;1`；
- target 三个 7 段 block 与三个显式冻结 verifier 的真值一致；
- source、lure、oracle 和 false mindset 都不包含目标卡路径；
- lure 的 R 标签、成本和路径与目标完全解耦，copy probe 与 target gold 不同；
- 21 段顺序、路径分隔符与提示角色盲化均被强制。

独立 first-hit DFS 不调用 verifier 的 UCS，复核三个目标层分布为 `{17:1,18:2}`、
`{17:1,19:3}` 和 `{18:1,19:3}`。

## 评测工具扩展

单一 21 段 exact 会掩盖三个查询中已经完成的部分。`mb report` 因此新增通用
`--part-group-size N`：只有一组内所有字段都正确才算 group exact；只有所有字段都出现才算 group
observed。它同时输出 group accuracy/coverage、source gain、oracle gain、source-vs-lure selectivity 和
oracle-vs-false selectivity；不整除 N 的答案会列为 incompatible，而不会静默混算。

本题使用：

```bash
.venv/bin/mb report \
  --database artifacts/runs/formal-p5-certificate-policy-gpt56sol.sqlite \
  --experiment-id EXPERIMENT_ID \
  --part-group-size 7
```

## GPT-5.6-sol 三样本结果

Matrix OpenAI-compatible API，16,384 输出 tokens；以下实验均无截断。单样本 24K 预试中 target-only
正确识别三张卡，但漏掉 γ 的成本 18 唯一路径并只输出“无解”；source 和 lure 当次均全对。该现象未在
三样本中稳定复现，不能作为迁移结论。

### solved-reference 三条件

| 条件 | case exact | parts | coverage | 7 段 block | block coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| target-only | 0/3 | 50/63 | 100% | 1/9 | 100% |
| with-source | 0/3 | 34/63 | 68.3% | 2/9 | 66.7% |
| with-lure | 1/3 | 54/63 | 100% | 4/9 | 100% |

三个 target-only 样本都识别对 K13/K2/K6，但 K2 都把旧成本 18 层错误地保留下来。典型错误是把成本
17 的最优路径命中目标后再追加 K3，当作新的成本 18 目标路径；这违反“首次满足完整目标即停止”。

source 没有稳定增益：逐段反而为 -25.4pp，一次试次只输出“无解”。虽然 source 的 block gain 是
+11.1pp，但 coverage 下降，且 source-vs-lure block selectivity 为 -22.2pp。路径解耦消除了精确复制，
却没有让 solved lure 成为可靠的有害控制；额外解题上下文和运行方差仍可能帮助搜索。因此不能报告
solved source schema transfer。

### procedure-only oracle/false

在同一三样本实验中，两种提示都不含任何卡号、路径或答案数值：

| 条件 | case exact | parts | coverage | 7 段 block | block coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| oracle mindset | 0/3 | 52/63 | 100% | 2/9 | 100% |
| false mindset | 0/3 | 44/63 | 100% | 0/9 | 100% |

oracle-vs-false exact selectivity 为 0，但 part selectivity 为 +12.7pp，block selectivity 为 +22.2pp。
false mindset 的输出会把同一份基线证书复制给三个查询，说明控制按预注册方向生效；oracle 则能更常
正确处理 K13，并恢复 K6 的新最优分支。不过 K2 的 first-hit runner-up 陷阱仍未解决，所以还不能声称
完整程序性迁移成功。

另一个 target/oracle 配对三样本中，oracle 将 coverage 从 68.3% 提到 100%、parts 从 32/63 提到
55/63、blocks 从 1/9 提到 4/9；对应 part gain +36.5pp、block gain +33.3pp，exact gain 仍为 0。
这证明方法提示改善了答案完整性和局部搜索，但效应大小存在明显运行方差。

## 结论与下一轮

1. 属性谓词识别在所有完整 target-only 输出中均正确；当前难点已从表面卡号定位转移到多查询最优性搜索。
2. K2 稳定暴露 stopping-time 错误：模型把首次命中后的冗余扩展误当成 runner-up 路径。
3. procedure-only 正确/错误 mindset 出现正 part 与 block selectivity，是目前比 solved source 更干净的
   迁移信号，但 exact 仍为 0，需跨实例复现。
4. 下一轮应增加 first-hit trap 诊断与同构 K2 变体，显式区分“最终状态满足目标的序列”和“首次命中
   目标即停止的路径”；随后再扩到 top-k 非空成本层。

## 复现

```bash
.venv/bin/mb validate data/manifests/formal-p5-certificate-policy-joint.json --strict-v1
.venv/bin/mb audit data/manifests/formal-p5-certificate-policy-joint.json
.venv/bin/mb verify all --dataset data/manifests/formal-p5-certificate-policy-joint.json
.venv/bin/pytest -q tests/test_formal_p5_certificate_policy.py tests/test_metrics.py
```

API 凭据只经环境变量或终端隐藏输入传入；实验 SQLite 位于 ignored 的 `artifacts/runs/`。
