#!/usr/bin/env python3
"""SO-101 evaluation success rate calculator.

Reads success/failure marks from command line and prints statistics.

Usage:
    python src/scripts/eval_stats.py s s f s s s f s s s
    # Output: 总轮数: 10, 成功: 8, 成功率: 80.0%

Mark conventions (case-insensitive):
    s / 1 / y / ✓ / success  -> success
    anything else            -> failure
"""

import sys

# Success markers (case-insensitive)
_SUCCESS_MARKS = {"s", "1", "y", "✓", "success", "true"}

# Failure markers (case-insensitive) - explicit, for clarity in logs
_FAILURE_MARKS = {"f", "0", "n", "✗", "fail", "false"}


def main():
    if len(sys.argv) <= 1:
        print("用法: python eval_stats.py <标记1> <标记2> ...")
        print("  成功标记: s / 1 / y / ✓ / success")
        print("  失败标记: f / 0 / n / ✗ / fail")
        print("  例: python eval_stats.py s s f s s s f s s s")
        sys.exit(1)

    marks = sys.argv[1:]
    total = len(marks)
    success = 0
    failure = 0
    unknown = []

    for i, m in enumerate(marks, 1):
        key = m.lower().strip()
        if key in _SUCCESS_MARKS:
            success += 1
        elif key in _FAILURE_MARKS:
            failure += 1
        else:
            unknown.append((i, m))

    if unknown:
        print(f"警告: {len(unknown)} 个标记无法识别: {unknown}")
        print("  已忽略未知标记，仅统计成功/失败。")

    if total == 0:
        print("没有输入任何标记。")
        sys.exit(1)

    rate = success / total * 100
    print(f"总轮数: {total}")
    print(f"成功:   {success}")
    print(f"失败:   {failure}")
    print(f"成功率: {rate:.1f}%")


if __name__ == "__main__":
    main()
