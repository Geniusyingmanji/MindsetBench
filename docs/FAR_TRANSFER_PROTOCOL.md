# 远域同 mindset 硬题构造协议（far-transfer protocol）

> 适用范围：所有希望进入 `calibration`/`test` 的 L2–L4 题。不满足本协议的题只能标为 `sanity`。
> 配套工具：`mb audit <dataset> --surface [--surface-table]`、`with-both` 评测条件、`selection_loss` 指标。

## 1. 为什么要有这份协议

2026-09-03 复盘发现，`formal35`、`hss20`、`hss-active8` 与首批 `expansion20` 虽然都通过了 schema 校验、
verifier 与 transfer-design 审计，却没有一题真正测到迁移：

| 症状 | 表现 | 后果 |
| --- | --- | --- |
| 目标题是 source 的同一形式化系统改名 | P2 链五级全部复用“去向:形态数,谱类”边表；L3 是完全重命名同构，L4 只再改一条边权 | 按 SPEC 五成分定义只翻了 Surface，实为 L1；GPT-5.6-sol 在 L0–L3 全对 |
| 目标题把形式结构原样写进题面 | HSS P6 目标逐句给出“预警/压制/支撑/掩护”有向边；active 题给出完整候选×查询回复矩阵 | 识别步骤为零，三条件 72/72、24/24 |
| 问句点名操作与答案空间 | “求恰好四条蓝边的方案数”“FATAL 只能选 NONE 或 P-CONTROLS-G” | 模型只需执行 |
| 难度只能靠规模 | 8 阶多项式行列式、16 张操作卡、32K 输出 | 要么天花板，要么算力地板；source 给的是计算脚手架而非框架，gain 为 0 |

量化证据（字符 bigram Jaccard，越低越远）：旧 85 题库 L2/L3/L4 的源目标文字重合为 0.09/0.04/0.03，
逐级单调下降；类型化扩展的 L3/L4 为 0.16/0.22，比旧库 L1 还近。类型化 L3/L4 共 65 题中有 43 题，目标题与
source 的符号重合不低于与 lure 的重合，也就是 source 才是表面最近的参考题，与设计意图相反。

根本原因：formal 链考的是**算法**（矩阵树、SCM 传播、不动点闭包、最短路证书）。算法需要同一种输入表示，
所以目标题只能换名字。真正能远域迁移的是**框架型 mindset**：守恒与不变量、信噪底、亚群混合、剩余地平线、
阴性证据、共同上游、可信承诺、瓶颈转移。旧库多跳链的 hop-4/hop-5 正是这种模板。

## 2. 十条构造规则

1. **识别难，执行易。** 框架选对之后剩余计算 5 步内手算完成且可穷举验证。20–60% 的冷启动窗口应来自
   识别失败率，不来自算术或搜索失败率。
2. **目标题写情境，不写换装的形式系统。** 不给整理好的关系表、规则层级、回复矩阵；不出现 source 的谓词词；
   结构从时间线、日志、配置、纪要、账目中恢复，需要恢复的事实要少而关键。
3. **问句只问该领域的自然决策。** 能不能排期、该合并吗、崩溃在哪个函数、先投哪里、哪项措施可信。
   映射、系数、码本这类 schema 内部对象不进主问句。
4. **诱饵是目标领域自己的标准做法。** 数一致意见、按覆盖面排序、比长期平均值、看罚金大小。预注册 decoy
   答案；target-only 的错误回答应集中命中 decoy，否则难度来自噪声。
5. **关键事实靠可行性或一致性推断，不靠陈述。** 例如“影像 14:00 起可调阅”加“11:20 签署”推出该意见只能依据报告。
6. **把著名题反过来用。** 表面高度匹配某道经典题但改一条关系；模型对经典题的记忆就是诱饵。
7. **L3 的 broken relation 必须由领域语义带出。** “换回需要一周洗脱”是；“一条边权 4 改成 9”不是。
8. **source 对目标题在计算上无用。** 不共享数字、字母、格式和中间结果，只共享关系层的表述。
   检验：H3（只给 mindset 陈述）的增益应接近 H4（给完整源解答）且远高于 H0。
9. **一个 mindset 建多个互远实例。** L2/L3/L4 三个目标必须彼此也远；任一实例做 source 都应给其余实例相近
   增益（source-invariance）。
10. **加“不该迁移”的目标。** 表面像、缺关键关系，正确答案是不用该 schema；每个家族至少一题（下一批）。

## 3. 五级在本协议下的含义

| 级 | 保持 | 变化 | 机械闸门 |
| --- | --- | --- | --- |
| L0 | 全部 | 参数 | 不门控 |
| L1 | Domain/Model/Method/Schema | Surface | 不门控 |
| L2 | Model/Method/Schema | 学科、文体、表征 | 门控 |
| L3 | Schema 与核心关系 | 加入一条由领域语义带出的 broken relation，照搬源方法得到预注册错误答案 | 门控 |
| L4 | 仅 Schema | Model 与 Method 全换（计数→概率、来源集→路径、逐期累积→截止可行性） | 门控 |

## 4. 自动闸门：`mb audit --surface`

对 `calibration`/`test` 中 L2 及以上的题：

| 检查 | 规则 | 结果 |
| --- | --- | --- |
| `surface-shared-template` | source 与 target 复用同一记法模板（边表 `X→Y:n`、`LABEL=CODE`、长位串、竖线表） | ERROR |
| `surface-lexical-overlap` | source/target 字符 bigram Jaccard 大于 0.12 | ERROR |
| `surface-lure-farther-than-source` | lure 与 target 的文字重合低于 source 与 target 的重合 | WARNING |

`sanity`/`dev` 题只报 WARNING。阈值 0.12 以旧 85 题库校准：远域题在 0.01–0.09，改名链在 0.15–0.8。
闸门是表征层的，它抓得住改名同构，抓不住“关系图写成句子”这类显式结构，后者靠规则 2、3 与人工审计。

## 5. 新评测条件与指标

- `with-both`：同时给 source 与 lure 的已解题，不标注、顺序由 case id 哈希决定并记录在 prompt metadata。
  它直接测量“表面相似的参考题在旁边时，模型还能不能选对结构”。
- 指标：`with_both_gain = acc(with-both) − acc(target-only)`；`selection_loss = acc(with-source) − acc(with-both)`；
  `lure_answer_rate_by_condition` 记录最终答案等于预注册 lure 答案的比例。
- 推荐首轮矩阵：`target-only / with-source / with-lure / with-both`，每格 3 样本，先只跑 `far20-hard.json`
  的 12 道 L2–L4。

## 6. 每题必备的形式世界

verifier 不信任存储答案：gold、lure 答案、copy probe 三者由同一个形式世界分别重算（来源根计数、条件概率、
路径枚举、有限期数 EV、收益比较）。此外每个 verifier 检查：题面含有推断所需的关键事实短语；L2 及以上
题面不含图式标签词（如“独立见证”“阴性证据”“探索/利用”“可信承诺”）；copy probe 不等于 gold；
lure 世界确实使 copy probe 成立。

## 7. 校准与晋级

1. 先跑 `target-only`，三样本、两档模型。整题 exact 落在 20%–60% 才继续；≥80% 降为 sanity。
2. 错误回答的 copy-probe 命中率应不低于 50%，否则回炉（难度来自噪声）。
3. `with-source − target-only ≥ +15pp`，且 `with-both` 的 gain 显著大于 0；`selection_loss` 报告为独立结果。
4. H3 与 H4 的增益差应小于 H3 与 H0 的增益差，否则 source 起作用的是示例而不是框架。
5. 以上任何一项不达标都如实报告，不删题；只按结构质量、无泄漏与难度窗口决定进入 hidden test。

## 8. 难度旋钮

关键事实埋得多深（与相关记录相隔多少行）、诱饵数字有多好看（6 份一致意见对门槛 3）、要拼接的文档有几份、
表面像不像某道经典题、稳妥选项与不确定选项的期望差多大。这些旋钮不改变形式世界，只改变识别成本；
调节它们，而不是增加节点数与操作数。
