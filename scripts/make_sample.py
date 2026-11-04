"""[EN] User-level sampling: keep all rows of users with user_id % MOD == 0 so trajectories stay complete.
Usage: python scripts/make_sample.py data/UserBehavior.csv data/sample_5pct.csv 20

按用户抽样：保留 user_id % MOD == 0 的全部行为，保证每个用户轨迹完整。
用法：python scripts/make_sample.py data/UserBehavior.csv data/sample_5pct.csv 20
"""
import sys

src, dst, mod = sys.argv[1], sys.argv[2], int(sys.argv[3])
kept = total = 0
with open(src, "r", encoding="utf-8") as fin, open(dst, "w", encoding="utf-8", newline="\n") as fout:
    for line in fin:
        total += 1
        if int(line.split(",", 1)[0]) % mod == 0:
            fout.write(line)
            kept += 1
print(f"total={total}, kept={kept}")
