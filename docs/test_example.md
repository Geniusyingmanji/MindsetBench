# 评测输入示例：历史文献 → 手术排期

本页使用 `FAR-INDEP-L3-01` 展示一个 far case 如何从 YAML 变成模型实际收到的单轮 Chat Completions 请求，
以及输出如何被自动判分。题目定义位于
[`data/v1/far-evidence-independence-chain.yaml`](../data/v1/far-evidence-independence-chain.yaml)。

> `docs/cases.md` 中的通俗说明不会输入模型。主评测也不会暴露 target gold、source-target mapping、copy probe、
> lure 的结构差异说明或 verifier。

## 1. Case 中存了什么

该 case 包含：

- **source**：地方志水利年代考订题、完整解答和答案 `3;确证`；
- **target**：不可逆手术排期题、答案格式和隐藏的标准答案；
- **lure**：同为医院排期、但只数一致意见的旧规程题及其解答；
- **mapping**：史料来源与临床一手证据之间的构造映射，只用于审计；
- **copy probe**：机械照搬 lure 时会给出的确定错误答案；
- **verification**：根据时间线、角色排除与证据来源重算答案的程序。

构造 prompt 时使用 `case.prompt_view()`，其中没有 target gold 和 copy probe。主评测只从其余材料中选择 condition 所需的内容。

## 2. 所有条件共用的输入

每次请求都使用同一个 system message：

```text
你是一个严谨的问题求解器。只依据用户提供的材料作答。
```

四个主要条件都包含同一份目标题：

```text
【目标题】
清源医院《不可逆手术排期规程》第 7 条：排期前须有至少 3 份相互独立且结论一致的评估；
评估只有在评估者签署前接触过至少一种一手证据（影像原片、组织切片或亲自查体）时才算独立；
拟主刀医师的评估不计入。

患者 K 当日记录节选：
08:30 入院登记；
09:10 MRI 扫描完成；
10:30 影像科 R 医师签发报告，结论“符合 X 病变”；
10:45 报告经院内系统推送给会诊医师 A、B、C、D 及拟主刀 E；
11:20 A（神经外科）签署会诊意见，同意 X；
11:40 B（肿瘤内科）签署，同意 X；
12:05 D（放疗科）签署，同意 X；
13:15 信息科通告：因 PACS 系统迁移，会诊端影像原片自 14:00 起方可调阅，此前只能查看文字报告；
14:20 病理科：活检切片已取材，报告预计明日 09:00 出；
15:30 C（神经内科）调阅影像原片后签署，同意 X；
16:00 E 查体并调阅影像原片后签署，同意 X，建议今日排期。

问：
(1) 按规程，今日能否排期？
(2) 下列单项措施中，哪些能单独使今日排期合规（若今日已可排期，则各项均填 NO）：
M1 请会诊医师 F 阅读报告后签署意见；
M2 请 A 调阅影像原片后重新签署；
M3 等待明日病理报告；
M4 请 R 补充一份更详细的影像报告；
M5 请 D 与 R 电话讨论后重新签署；
M6 请外院专家 G 远程调阅影像原片并签署。

【答案格式】
SCHEDULE=<YES|NO>;M1=<YES|NO>;M2=<YES|NO>;M3=<YES|NO>;M4=<YES|NO>;M5=<YES|NO>;M6=<YES|NO>

请给出必要的推理过程，并在最后一行严格输出：ANSWER: <答案>。
多段答案使用分号分隔，不添加单位或解释。
```

仓库中的 YAML 使用折叠文本，CLI 渲染时可能把部分换行折叠为空格；内容不变。

## 3. `target-only`

`target-only` 的 user message 只有：

```text
请解下面这道题。

<目标题与答案格式>

<统一输出要求>
```

模型看不到历史文献 source，也看不到“共享同一上游的一致信号只构成一份证据”这个 schema 名称。
该条件测量模型在没有迁移提示时能否独立恢复证据来源结构。

可直接查看完整渲染结果：

```bash
.venv/bin/mb prompt FAR-INDEP-L3-01 target-only \
  --dataset data/manifests/far50.json
```

## 4. `with-source`

`with-source` 在目标题前加入完整的已解历史题。下面为便于阅读的压缩展示，CLI 命令会输出未经缩写的实际 prompt：

```text
先阅读一道已解出的参考题，再解决目标题。

【参考题】
县志编修组需确定永丰堰的建成年份。现有六种记载都写康熙十二年：
甲、乾隆《县志·水利》；
乙、道光《县志·水利》，自述“水利一门悉据乾隆志”；
丙、光绪《府志》，注明“县境水利采道光县志”；
丁、雍正年间《张氏族谱》，记康熙十二年建成；
戊、落款康熙十四年的残碑，记康熙十二年建成；
己、民国《吴氏族谱》，注明水利材料摘录自光绪府志。

规程要求追溯到最初的一手来源；转录材料与其来源合并。
问：共有几个独立见证，应定为何级？

【参考题解答】
乙据甲，丙据乙，己据丙，四者同出乾隆志，只算一个见证；
丁与戊分别是另外两个独立见证。因此共有三个独立见证，定为确证。
计数对象是来源链的根，不是记载条数。

【参考题答案】
3;确证

<目标题与答案格式>

<统一输出要求>
```

source 的解答明确展示“追踪来源根”的做法，但不会给出下列显式映射：

```text
史料互相转录        ↔ 医生只看到同一份报告
追踪最初史料来源    ↔ 追踪签字前接触的一手证据
```

模型必须自己识别并迁移这层关系。`with-source - target-only` 的准确率差是主要的正迁移指标。

```bash
.venv/bin/mb prompt FAR-INDEP-L3-01 with-source \
  --dataset data/manifests/far50.json
```

## 5. `with-lure`

`with-lure` 使用与 `with-source` 完全相同的“已解参考题”包装，但参考内容换成医院旧规程。
下面同样是压缩展示：

```text
先阅读一道已解出的参考题，再解决目标题。

【参考题】
同院另一患者 J 的记录中，R、A、B、D、E 都签署了一致意见。
该科室沿用的旧版规程只要求“至少 3 份结论一致的评估”。
问今日能否排期，以及 M1–M6 是否有必要。

【参考题解答】
旧版规程只数一致评估：R、A、B、D、E 共 5 份，大于等于 3，直接可排期；
各项补救均无必要。

【参考题答案】
SCHEDULE=YES;M1=NO;M2=NO;M3=NO;M4=NO;M5=NO;M6=NO

<目标题与答案格式>

<统一输出要求>
```

prompt 不会出现“错误参考题”“lure”或“不要照搬”等提示。模型要自己发现参考题只数人数，而目标题要求证据独立性。

若模型照搬参考答案，就会命中预注册 copy probe：

```text
SCHEDULE=YES;M1=NO;M2=NO;M3=NO;M4=NO;M5=NO;M6=NO
```

```bash
.venv/bin/mb prompt FAR-INDEP-L3-01 with-lure \
  --dataset data/manifests/far50.json
```

## 6. `with-both`

`with-both` 同时加入 source 和 lure，但称为“参考题一、参考题二”，不标注身份：

```text
先阅读两道已解出的参考题。它们与目标题的相关性未知，可能有一道、两道或没有一道
与目标题共享解题结构；请自行判断后再解决目标题。

【参考题一】
<一份已解参考题>

【参考题二】
<另一份已解参考题>

<目标题与答案格式>

<统一输出要求>
```

参考题顺序由 case ID 的 SHA-256 哈希确定，避免所有题都把 source 固定放在同一位置。对本 case，实际顺序是：

1. 参考题一：医院旧规程 lure；
2. 参考题二：地方志 source。

该条件测试：当“同领域但结构错误”的参考题与“跨领域但结构正确”的参考题同时出现时，模型会根据表面还是结构选择。

```bash
.venv/bin/mb prompt FAR-INDEP-L3-01 with-both \
  --dataset data/manifests/far50.json
```

## 7. 发给模型服务的请求

runner 把 system 和渲染后的 user prompt 组成一次 OpenAI-compatible Chat Completions 请求：

```json
{
  "model": "gpt-5.6-sol",
  "messages": [
    {
      "role": "system",
      "content": "你是一个严谨的问题求解器。只依据用户提供的材料作答。"
    },
    {
      "role": "user",
      "content": "按 condition 渲染出的完整提示词"
    }
  ],
  "temperature": 0,
  "max_tokens": 8192,
  "seed": 123456
}
```

认证通过 HTTP header 传入，不进入 prompt 或结果正文：

```text
Authorization: Bearer <MINDSETBENCH_API_KEY>
```

`seed` 根据实验 seed、case ID、condition 和 sample index 稳定生成。服务若不支持某个可选参数，provider 会协商调整或移除，
并把调整记录在结果 metadata 中。

## 8. 期望输出与自动判分

模型可以在前面写推理，但最后一行必须为：

```text
ANSWER: SCHEDULE=NO;M1=NO;M2=YES;M3=NO;M4=NO;M5=NO;M6=YES
```

答案含义：

- A、B、D 在原片开放前签字，只能依赖 R 的同一份报告，不能各算一份独立证据；
- C 看过原片，可独立计入；
- E 是拟主刀，按规程排除；
- 当天只有 R、C 两份可计入评估，所以不能排期；
- M2 让 A 接触原片后重签，可新增第三份；
- M6 让外院专家独立看片，也可新增第三份；
- 其余单项措施不能使“今日”的独立评估达到三份。

grader 会提取模型输出中最后一个 `ANSWER:`，按分号切分并逐项比较，同时记录：

- 整题 exact；
- 各 answer part 是否正确；
- 是否缺少或多出字段；
- 是否命中 lure answer；
- 是否命中 copy probe。

推理文本目前用于人工失败审计，不直接参加 exact 判分。

## 9. 安全复现

查看四种输入不调用模型 API，可以分别运行：

```bash
.venv/bin/mb prompt FAR-INDEP-L3-01 target-only --dataset data/manifests/far50.json
.venv/bin/mb prompt FAR-INDEP-L3-01 with-source --dataset data/manifests/far50.json
.venv/bin/mb prompt FAR-INDEP-L3-01 with-lure --dataset data/manifests/far50.json
.venv/bin/mb prompt FAR-INDEP-L3-01 with-both --dataset data/manifests/far50.json
```

也可以离线检查一个答案如何被判分：

```bash
printf '%s\n' 'ANSWER: SCHEDULE=NO;M1=NO;M2=YES;M3=NO;M4=NO;M5=NO;M6=YES' | \
  .venv/bin/mb grade FAR-INDEP-L3-01 - --dataset data/manifests/far50.json
```

当前 `mb run` 按数据集运行，尚无 `--case-id` 单题过滤参数。直接传入 `far50.json` 会运行 50 题；
四个条件、每题三样本合计 600 次调用，不应把它误当作单题示例。正式批量运行前先用 `mb plan-run` 检查调用规模，
命令见仓库根目录 [`README.md`](../README.md)。

正式比较关注：

```text
transfer_gain          = acc(with-source) - acc(target-only)
structural_selectivity = acc(with-source) - acc(with-lure)
with_both_gain         = acc(with-both) - acc(target-only)
selection_loss         = acc(with-source) - acc(with-both)
```

提示构造实现见 [`src/mindsetbench/prompting/builders.py`](../src/mindsetbench/prompting/builders.py)，
API payload 见 [`src/mindsetbench/runner/providers.py`](../src/mindsetbench/runner/providers.py)，
答案抽取与判分见 [`src/mindsetbench/grading/grader.py`](../src/mindsetbench/grading/grader.py)。
