"""题库校验与合并：python3 scripts/validate.py
校验 data/cases/*.jsonl 的 schema、ID 唯一性、lure 齐备性、线程命名、多跳链衔接，
通过后重建 data/all.jsonl。"""
import collections
import glob
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED = {"id", "level", "thread", "schema_name", "source", "target",
            "mapping", "lure", "provenance", "verified"}
ALLOWED_EXTRA = {"chain", "hop", "method", "derivation", "history_note"}
CANON = {"A": "A-约束枚举", "B": "B-不变量验证", "C": "C-分解规划",
         "D": "D-元认知控制", "E": "E-信噪判别", "F": "F-逆问题", "G": "G-混合建模"}


def main():
    files = sorted(ROOT.glob("data/cases/*.jsonl"))
    all_rows, problems = [], []
    for f in files:
        for i, line in enumerate(open(f), 1):
            if not line.strip():
                continue
            r = json.loads(line)
            if REQUIRED - set(r):
                problems.append(f"{f.name}:{i} {r.get('id')} missing {REQUIRED - set(r)}")
            if set(r) - REQUIRED - ALLOWED_EXTRA:
                problems.append(f"{f.name}:{i} {r.get('id')} extra {set(r) - REQUIRED - ALLOWED_EXTRA}")
            canon = CANON.get(r["thread"][0])
            if canon and r["thread"] != canon:
                problems.append(f"{r.get('id')} thread 未归一化: {r['thread']}")
            for k in ("domain", "problem", "solution", "answer"):
                if k not in r.get("source", {}):
                    problems.append(f"{r.get('id')} source missing {k}")
            for k in ("domain", "problem", "answer", "answer_type"):
                if k not in r.get("target", {}):
                    problems.append(f"{r.get('id')} target missing {k}")
            if r["level"] >= 2 and not r.get("lure") and "multihop" not in str(r.get("chain", "")):
                problems.append(f"{r.get('id')} L2+ 缺 lure")
            all_rows.append(r)

    dup = [x for x, c in collections.Counter(r["id"] for r in all_rows).items() if c > 1]
    if dup:
        problems.append(f"重复 ID: {dup}")

    for ch in sorted({r["chain"] for r in all_rows if "multihop" in str(r.get("chain", ""))}):
        hops = sorted([r for r in all_rows if r.get("chain") == ch], key=lambda r: r["hop"])
        for a, b in zip(hops, hops[1:]):
            if b["source"]["problem"].strip() != a["target"]["problem"].strip():
                problems.append(f"{ch} hop{b['hop']} 与上一跳衔接断裂")

    if problems:
        print("FAILED:")
        for p in problems:
            print(" -", p)
        sys.exit(1)

    with open(ROOT / "data/all.jsonl", "w") as out:
        for r in sorted(all_rows, key=lambda r: (r["level"], r["id"])):
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    lv = collections.Counter(r["level"] for r in all_rows)
    th = collections.Counter(r["thread"][0] for r in all_rows)
    print(f"PASS: {len(all_rows)} cases -> data/all.jsonl")
    print("levels:", dict(sorted(lv.items())))
    print("threads:", dict(sorted(th.items())))


if __name__ == "__main__":
    main()
