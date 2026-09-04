# far20：远域同 mindset 硬题首批构造报告

日期：2026-09-03。本批按 [`FAR_TRANSFER_PROTOCOL.md`](FAR_TRANSFER_PROTOCOL.md) 构造，共四个家族、20 题，
全部 `split: calibration`；尚未进行模型校准，本页只报告构造与静态验证结果。

## 1. 四个家族

| 家族 | mindset | source 域 | L2 / L3 / L4 目标域 | 答案形式 | 预注册诱饵 |
| --- | --- | --- | --- | --- | --- |
| `far-evidence-independence-v1`（P7） | 共享同一上游的一致信号只构成一份证据 | 地方志年代考订 | CI 合并门禁 / 手术排期审核 / 储罐联锁共因失效 | 决策加逐项补救；概率加最优改造 | 数一致信号 |
| `far-negative-evidence-v1`（P2） | 未出现的预期信号与出现的信号同样切割候选集 | 食品供应链溯源 | 故障定位 / 编年史成书区间 / 红外相机路线重建 | 唯一候选；年份区间；路径 | 按覆盖面排序、全部沉默作上界、最短路 |
| `far-horizon-exploration-v1`（P1） | 试探的价值由其后剩余的可利用时间决定 | 越冬觅食 | 施工队选择（邮件推日期）/ 术前用药（两周判断加洗脱）/ 截止前投稿 | 两个地平线下的首步决策加阈值 | 知情期望更高就先试；照搬源阈值 |
| `far-credible-commitment-v1`（P8） | 承诺的可信度来自承诺人失去反悔的能力 | 云接口停用公告 | 零售退差价方案 / 边境停火安排 / 罢工威胁收益比较 | 四项措施逐项 CREDIBLE/CHEAP | 有强制或罚金即可信；任何第三方即独立 |

每个家族的 L0、L1 是同域锚点；L2 为跨学科、跨文体、跨表征的同构；L3 加入一条由领域语义带出的 broken
relation（时间可行性推断加角色排除、沉默有效性条件、两周判断加洗脱期、第三方受承诺人控制）；L4 更换
Model 与 Method（条件概率、图上路径、截止可行性、事后收益比较），只保留 mindset。

## 2. 表面距离

`mb audit data/manifests/far20.json --surface-table` 的 source/target 字符 bigram Jaccard（越低越远）：

| 家族 | L2 | L3 | L4 | 与之对照：formal P2 链 L2–L4 |
| --- | ---: | ---: | ---: | ---: |
| evidence-independence | 0.02 | 0.01 | 0.01 | 0.22 且复用边表模板 |
| negative-evidence | 0.01 | 0.00 | 0.01 | |
| horizon-exploration | 0.03 | 0.05 | 0.02 | |
| credible-commitment | 0.05 | 0.07 | 0.08 | |

20 题无共享记法模板；12 道 L2–L4 全部通过闸门。唯一的 WARNING 是 `FAR-COMMIT-L2-01` 的 lure 文字略短于
source 与目标的重合（0.04 对 0.05）。

## 3. 静态验证

| 检查 | 结果 |
| --- | --- |
| `mb validate data/manifests/far20.json --strict-v1` | 20 题，0 error |
| `mb validate-cards data/manifests/far20-cards.json data/manifests/far20.json` | 4 cards，0 error |
| `mb audit data/manifests/far20.json --require-complete-chains --surface` | 0 error，1 warning |
| `mb verify all --dataset data/manifests/far20.json` | 20/20 PASS |
| 四个 verifier 模块的独立测试 | gold、lure、copy probe 由同一形式世界重算；篡改 gold 或删去关键事实即失败 |

verifier 各自的形式世界：来源根计数与时间可行性、共因条件概率（精确分数，0.0766 对独立假设的 0.0280）、
到达关系上的正负约束过滤、事件年份的有效上界、A 到 F 全部简单路径的时间与静默筛选、有限期数试探 EV
（阈值 3/2/2/4）、截止前改投可行性（5 个月）、承诺措施的控制者属性与工会事后收益比较。

## 4. 待校准

尚未调用任何模型。2026-09-04 尝试从本机运行时，`matrixllm.alipay.com` 解析到 Alipay 办公网关地址段
（110.76.x.x），TLS 握手被对端关闭，需要在能访问该端点的网络（公司 VPN 或办公网）上执行。一键脚本：

```bash
export MINDSETBENCH_API_KEY='...'
scripts/run_far20_calibration.sh gpt-5.6-sol            # 两阶段：先 target-only，再三个配对条件
scripts/run_far20_calibration.sh gpt-5.6-sol "$ENDPOINT" target   # 只跑 target-only 预筛
```

手动等价命令：

```bash
.venv/bin/mb plan-run --dataset data/manifests/far20-hard.json \
  --conditions target-only with-source with-lure with-both --samples-per-item 3

export MINDSETBENCH_API_KEY='...'
.venv/bin/mb run --dataset data/manifests/far20-hard.json \
  --database artifacts/runs/far20-hard.sqlite --experiment-id far20-hard-target-s3-v1 \
  --model gpt-5.6-sol --endpoint https://matrixllm.alipay.com/v1/chat/completions \
  --conditions target-only --samples-per-item 3 --max-output-tokens 4096
```

预注册判读：target-only 整题 exact 落在 20%–60% 且错误集中命中 copy probe，才继续 `with-source / with-lure /
with-both`；任何一题 target-only ≥ 80% 即降为 sanity 并按协议第 8 节调节难度旋钮，而不是加规模。
`selection_loss` 与 `with_both_gain` 作为独立结果报告。

## 5. 与本批同时完成的降级

82 道类型化 case 改为 `split: sanity` 并写入 `history_note`（见 [`../data/CASE_STATUS.md`](../data/CASE_STATUS.md)）。
它们仍可运行、仍通过 verifier，但不再计入迁移距离统计；`mb audit --surface` 对它们只报 WARNING。
