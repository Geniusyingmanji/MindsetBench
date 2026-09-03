# Humanities/Social-20 扩展目标

## 1. 为什么调整方向

现有 `formal35` 已证明类型化数据、配对提示、逐段判分、SQLite runner 和可执行 verifier 可以工作，
但题目仍明显偏数学：P2 依赖带权计数，P3 依赖线性 SCM，P5 依赖最短路与路径枚举，P6 依赖图匹配。
即使题面使用菌落、政策、档案等词汇，模型仍可把大部分任务还原为熟悉的数值或组合计算。

下一阶段不再以“增加状态数、操作数和答案段数”为主要难度来源，而改为：

> 在源题与目标题的词汇、学科、文体和表征都显著不同的前提下，只保留可迁移的关系图式；
> 让模型识别规范、论证、证据、角色和制度机制，同时继续提供唯一、可执行的结构真值。

这不是放弃形式化，而是把形式化从题面移到 verifier：被测模型读自然语言材料，评测端用规则系统、
论证图、类型图匹配或有限机制模型验证答案。

## 2. 可验收目标

首个交付包暂名 `hss20`，包含四条固定源 L0–L4 链，共 20 题。

当前进度（2026-09-03）：四条链已形成可运行的 `hss20`，20/20 题完成；
严格数据校验、schema-card 校验、迁移设计审计和独立 verifier 均已通过。尚未进行模型难度校准，
因此不能据此声称题目已经达到 20%–60% 的目标窗口。

| 维度 | 目标 |
| --- | --- |
| 人文社科覆盖 | 至少 16/20 个 target 位于法律、历史、公共政策、组织治理、传播或文化分析 |
| 高等级距离 | 8 个 L3/L4 全部跨学科且跨文体；至少一半为技术/科学源 → 人文社科目标，另一半为远距离人文社科互迁 |
| 非数值答案 | 至少 16/20 使用标签、集合、顺序、对应关系或三值方向；不得把长算术作为主难度 |
| 结构适配 | 每个 L3/L4 至少删除或改写一条源关系，并提供可确定命中的照搬错误答案 |
| 可执行真值 | 20/20 具有独立 verifier；gold、lure 和 copy probe 全部可复算 |
| 难度净空 | calibration 模型 target-only exact 目标为 20%–60%，避免基础链 ceiling 和联合题 exact floor |
| 污染控制 | 材料中的制度、事件、人物和文本均原创或深度改写，不依赖模型记忆真实判例或著名历史类比 |

数字是验收门槛，不是通过筛选制造正迁移。题目只按结构质量、无泄漏和 target-only 难度校准；
`with-source` 是否产生正增益必须如实报告，不能因为结果为负就删题。

## 3. 四条优先链

### HN：规范、例外与判例区分（P4）

- **核心 mindset**：先求适用规则，再处理例外、优先级和 defeater；表面相似事实只有触及核心理由时才足以区分先例。
- **源域候选**：桌游竞赛纪律、实验室访问章程或软件权限政策。
- **目标域候选**：虚构行政复议、劳动申诉、档案开放或文化遗产借展规则。
- **机器真值**：Datalog/优先规则闭包；输出适用规则、违规对象或决定性区分因子。
- **L4 变化**：源题给显式规则，目标题只给若干已决案例及理由，需要先恢复规范层级，再处理一个新 defeater。
- **实现状态**：已完成。L0/L1 为代码访问规则，L2 为虚构博物馆出借，L3 为劳动申诉协议与纪要，
  L4 为公共档案先例摘要；L4 新增“法院解密令仅覆盖契约封存”的窄关系，机械照搬源题会多拒绝 `U5`。

### HE：论证图式与证据独立性（P7）

- **核心 mindset**：识别论证类型，并提出真正针对该图式的 critical question；多条证言若共享同一上游来源，不能算独立 corroboration。
- **源域候选**：工程故障审查、医学委员会建议或科研同行评议。
- **目标域候选**：匿名史料归属、艺术品来源证明、新闻消息链或公共政策听证。
- **机器真值**：带类型论证图与 attack/support 关系；输出最关键 CQ、独立证据集合或结论状态。
- **L4 变化**：从显式“专家意见”迁移到混合档案材料，并加入引用链重合，使简单多数证据失效。
- **实现状态**：已完成。L2 将工程报告迁到新闻核验，L3 使用艺术品图录、展签和鉴定警报，
  L4 进一步把不同一手底本按共同编辑简报或送审包二次聚类；只按底本编号去重会误判 `H1/H4`。

### HA：历史类比与角色系统映射（P6）

- **核心 mindset**：按因果角色和关系映射，而不是按人物、时代或事件词汇匹配；同时识别会使建议失效的致命差异。
- **源域候选**：生态恢复、事故响应或组织重组。
- **目标域候选**：联盟形成、外交斡旋、制度改革或社会运动策略。
- **机器真值**：锚定的类型关系图匹配；输出角色对应、共享关系以及唯一 fatal difference。
- **L4 变化**：多数角色仍可对应，但目标中一条控制关系方向反转；照搬源行动将得到预注册错误结论。
- **实现状态**：已完成。L3 从外交编年及显著噪声角色恢复五边主链；L4 保留四条关系，
  但把治理节点约束压力组织反转为压力组织控制治理节点，使角色相似而行动建议失效。

### HM：制度机制与战略诊断（P8）

- **核心 mindset**：从叙述中区分可信承诺、昂贵信号、筛选、委托代理、道德风险和集体行动机制，并判断机制成立所需的可观察性或不可逆性。
- **源域候选**：分布式协议、访问控制、平台审核或供应链担保。
- **目标域候选**：联盟承诺、劳资谈判、公共资源治理、慈善机构监督或官僚授权。
- **机器真值**：有限行动/信息结构的约束求解；输出机制标签、缺失条件或方向性后果。
- **L4 变化**：源题的信号成本可验证，目标题中成本由第三方补贴，导致原来的“可信信号”关系失效。
- **实现状态**：已完成。L3 从公地会议纪要和附函追踪实际成本，L4 联合公开账册与秘密担保函，
  识别事前垫资和事后返还使机会主义者也能模仿，但不影响另一项真正删除未来选项的承诺。

P9 叙事/脚本暂列第二阶段探索项。只有当双人标注和程序化事件语法能把一致率稳定到可接受水平后，
才加入主指标；否则只作为 exploratory split。

## 4. 源题与目标题必须真的不同

新题不接受只替换名词的 reskin。L3/L4 必须同时满足：

1. **跨学科**：源和目标属于不同知识共同体，不能只是“工程流程 A → 工程流程 B”；
2. **跨文体**：至少跨越规则清单、证词摘录、案例摘要、历史叙事、会议纪要中的两种；
3. **跨表征**：一侧可显式给关系，另一侧需从自然语言材料恢复关系；不得复用同一变量字母、表格列名或编号模式；
4. **保核心、改局部**：`mapping.shared_relations` 保留 mindset，`removed_relations/added_relations` 明确说明为什么不能照搬；
5. **双向覆盖**：既包含技术/科学 → 人文社科，也包含法律 → 历史、历史 → 组织治理等人文社科内部远迁移；
6. **复杂度匹配**：source、target、lure 的阅读量、候选数和输出长度接近，避免靠上下文长度制造条件差异。

建议为每题保存一份与自然语言分离的中间表示：

```text
objects + typed_relations + priorities/attacks + shared_schema
        ↓ source mapping / target mapping
gold derivation + lure derivation + copy-probe derivation
```

Verifier 只读取题面可恢复的信息重建该表示，不直接信任存储的 gold。

## 5. 示例种子

| 源题 | 目标题 | 共享 mindset | 目标输出 |
| --- | --- | --- | --- |
| 实验室访客章程 | 虚构档案开放复议 | 高位禁止优先于一般许可，例外只覆盖一般规则 | 违规申请集合 |
| 医学专家委员会建议 | 匿名政治文书归属 | 专家意见需检验领域适格、独立性与证据基础 | 最关键 CQ 标签 |
| 生态恢复中的角色网络 | 多方外交斡旋纪要 | 按因果角色映射，并检查关系方向是否保持 | 角色对应 + fatal difference |
| 分布式系统不可逆提交 | 联盟公开承诺 | 删除未来选项才能使承诺可信 | 机制标签 + 缺失条件 |
| 软件审核的共享日志源 | 多份历史回忆录互相转引 | 共享上游来源不能形成独立佐证 | 独立证据集合 |
| 供应链质保与第三方补贴 | 公共人物的昂贵信号 | 成本只有由行动者承担且难以伪装时才有区分力 | 信号是否可信（三值） |

这些只是结构种子。正式题必须使用虚构实体，并为 source、target、lure 分别生成可执行真值。

## 6. 评测与晋级

每题保留 `target-only / with-source / with-lure / oracle-mindset / false-mindset`，但新增两个切片：

- `domain_direction`：technical→HSS、HSS→HSS；
- `reasoning_family`：norm、argument、analogy、mechanism。

预筛阶段使用两档模型、每格至少 3 样本；正式 calibration 每格至少 8 样本。报告：

1. case exact、part accuracy、coverage；
2. source transfer gain 与 paired bootstrap 区间；
3. source-vs-lure structural selectivity；
4. oracle-vs-false mindset selectivity；
5. copy-probe rate 与照搬错误命中率；
6. 按领域方向和推理家族分层的迁移梯度。

晋级 hidden test 前必须满足：题面无答案泄漏、verifier 与独立复算一致、target-only 落入难度窗口、
copy probe 不与 gold 重合。source gain 不作为删题门槛，只作为待测结果。

## 7. 代码交付计划

```text
data/schema_cards/hss-p4-norm-precedent-v1.yaml
data/schema_cards/hss-p7-argument-evidence-v1.yaml
data/schema_cards/hss-p6-historical-analogy-v1.yaml
data/schema_cards/hss-p8-institutional-mechanism-v1.yaml
data/v1/hss-*.yaml
data/manifests/hss20.json
data/manifests/hss20-cards.json
src/mindsetbench/verification/hss_*.py
tests/test_hss_*.py
docs/hss20-report.md
```

实施顺序采用逐链垂直切片：先完成一条链的 L0–L4、schema card、verifier 和负控制，确认整条工具链后再进入
下一推理家族。当前四条链均已完成。20 题全部通过
strict validate、schema-card audit、independent verifier 和泄漏扫描后，再调用模型进行正式 calibration；
开发阶段可以对单链做小样本冒烟测试，但不得据此筛除负迁移题。

完整数据包可独立复现：

```bash
.venv/bin/mb validate data/manifests/hss20.json --strict-v1
.venv/bin/mb validate-cards data/manifests/hss20-cards.json data/manifests/hss20.json
.venv/bin/mb audit data/manifests/hss20.json --require-complete-chains
.venv/bin/mb verify all --dataset data/manifests/hss20.json
```
