# MindsetBench

测量 LLM/agent 的 mindset（认知图式）跨学科迁移能力的 benchmark：以迁移距离为连续自变量（L0 同域同型 → L4 跨域远类比），配对式三条件评测（target-only / with-source / with-lure），全部机器可判。核心用途：区分 self-evolving 系统学到的是 trick（表面捷径，跨域归零）还是 meta-skill（可迁移图式，衰减平缓）。

## 快速导航

| 想了解 | 看 |
| --- | --- |
| 总体计划（背景、动机、三轴设计、路线图） | PLAN.md |
| 难度五级定义、测量协议、案例 schema | docs/SPEC.md |
| 五种题目构造方法对比 | docs/METHODS.md |
| 数学建模之外的图式范式调研（P1–P9） | docs/PARADIGMS.md 及 docs/research/ |
| 六条多跳长链简介（测迁移传递性） | docs/multihop-chains.md |
| 自进化方法试点评测结果与教训 | docs/pilot-report.md |
| 哪些题可用、哪些需修 | data/CASE_STATUS.md |

## 目录结构

```
PLAN.md               总体计划
docs/                 设计文档与调研报告
data/
  all.jsonl           全部题目（机器可读汇总，由 validate.py 生成）
  CASE_STATUS.md      题库分诊（ready / descaffold / audit / prototype-risk / dev）
  cases/              各题集（人读版 .md + 机器可读 .jsonl 成对）
harness/
  grade.py            判分器（整数精确、小数容差、多段逐段）
  prompts.py          三条件提示构造器
  sample.json         试点样本定义
  results/            试点原始结果与经验库
scripts/
  validate.py         schema 校验 + 链衔接检查 + 重建 all.jsonl
```

## 数据格式

每题一行 JSON（data/cases/*.jsonl）：id、level（0–4）、thread（A–G 认知线程）、schema_name（共享图式一句话）、source（源题：domain/problem/solution/answer）、target（目标题：domain/problem/answer/answer_type/tolerance）、mapping（对象映射 + 共享关系 + 翻转成分）、lure（表面相似异结构的干扰源）、provenance、verified（验证方式）。链案例另有 chain 与 hop 字段。L3 起的 mapping.varied 中标注"照搬源解法会得到的错误答案"，作为负迁移探针。

## 使用

```bash
python3 scripts/validate.py                 # 校验题库并重建 data/all.jsonl
python3 harness/prompts.py L3-A-01 target-only   # 生成某题某条件的评测提示
```

判分：`from harness.grade import grade_item; grade_item(item, model_output)`；被测模型须在最后一行输出 `ANSWER: <答案>`。

## 现状

题库 85 题（L0×2 / L1×15 / L2×19 / L3×30 / L4×19），七条认知线程全覆盖 L1–L4；固定源链 ×2 + 多跳长链 ×6；全部答案（含照搬错误答案与 lure 答案）经独立脚本验证。分诊与已知问题见 data/CASE_STATUS.md，路线图见 PLAN.md 第 7 节。
