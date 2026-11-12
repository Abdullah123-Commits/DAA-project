import math, random, sys, time, os, heapq
import tkinter as tk
from tkinter import filedialog

# CONSTANTS
DATA_DIR = "datasets"
SIZES = [random.randint(101, 1000) for _ in range(10)]
SEED = 420
INF = float("inf")
LOG_DEPTH = 2

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

# input file gen (Q2)
def generate_datasets(folder=DATA_DIR, seed=SEED):
    rng = random.Random(seed)
    os.makedirs(folder, exist_ok=True)

    def big_int(digits):
        s = str(rng.randint(1, 9)) + "".join(rng.choice("0123456789")  for _ in range(digits - 1))
        return ("-" if rng.random() < 0.5 else "") + s

    for k, n in enumerate(SIZES, start=1):
        vals = rng.sample(range(-10000, 10001), n)
        with open(os.path.join(folder, f"c_1D_{k:02d}.txt"), 'w') as f:
            f.write("\n".join(map(str, vals)) + "\n")

        pt_set = set()
        while len(pt_set) < n:

            pt_set.add((rng.randint(-5000, 5000), rng.randint(-5000, 5000)))
        pt_set = sorted(pt_set)

        rng.shuffle(pt_set)

        with open(os.path.join(folder, f"c_2D_{k:02d}.txt"), 'w') as f:
            f.write("\n".join(f"{x} {y}" for x, y in pt_set) + "\n")

        with open(os.path.join(folder, f"intmul_{k:02d}.txt"), "w") as f:
            f.write(big_int(n) + "\n" + big_int(n) + "\n")

    return len(SIZES) *3

# file reading
def _num(token):
    try:
        return int(token)
    except ValueError:
        return float(token)

def load_file(path):
    with open(path) as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if not lines:
        raise ValueError("The file is empty")
    if len(lines[0].split()) == 2:
        return "2d", [tuple(_num(t) for t in ln.split()) for ln in lines]
    if len(lines) == 2:
        return "mul", (int(lines[0]), int(lines[1]))
    return "1d", [_num(ln) for ln in lines]

# algorithms (Q3)
def closest_pair_1d(values):
    nums = sorted(values)
    steps = []

    def rec(lo, hi):
        size = hi - lo + 1
        if size > 2:
            return INF, None

        if size == 2:
            best = (nums[hi] - nums[lo], (nums[lo], nums[hi]))
            steps.append({"type": "base", "lo": lo, "hi": hi, "best": best, "text": f"Base case [{lo}..{hi}]: {nums[lo]}, {nums[hi]} -> d = {best[0]}"})

            return best

        mid = (lo + hi) // 2
        steps.append({"type": "divide", "lo": lo, "hi": hi, "mid": mid, "text": f"Divide [{lo}..{hi}] ({size} numbers) between index {mid} and {mid + 1}"})

        left = rec(lo, mid)
        right = rec(mid + 1, hi)
        cross = (nums[mid + 1] - nums[mid], (nums[mid], nums[mid + 1]))
        best = min(left, right, cross, key=lambda t: t[0])
        steps.append({"type": "combine", "lo": lo, "hi": hi, "mid": mid, "best": best,
                      "text": f"Combine [{lo}..{hi}]: left d = {left[0]}, right d = {right[0]}, "
                              f"cross d = {cross[0]} -> best d = {best[0]}"})
        return best

    d, pair  = rec(0, len(nums) - 1) if len(nums) >=2 else (INF, None)
    return d, pair, steps, nums


def karatsuba_multiply(x, y):
    sign = -1 if (x < 0) != (y < 0) else 1
    nodes, steps, stats = [], [], {"calls": 0}
 
    def rec(a_, b_, depth, parent):
        stats["calls"] += 1
        node = None
        if depth <= LOG_DEPTH:
            node = {"id": len(nodes), "depth": depth, "x": a_, "y": b_,
                    "children": [], "split": None, "z": None, "result": None}
            nodes.append(node)
            if parent is not None:
                nodes[parent]["children"].append(node["id"])
            steps.append({"type": "call", "node": node["id"]})
        nid = node["id"] if node else None
 
        if a_ < 10 or b_ < 10:                                # base case
            res = a_ * b_
        else:
            n = max(len(str(a_)), len(str(b_)))
            m = n // 2
            p = 10 ** m
            a, b = divmod(a_, p)                              # x = a*10^m + b
            c, d = divmod(b_, p)                              # y = c*10^m + d
            if node:
                node["split"] = (m, a, b, c, d)
            z2 = rec(a, c, depth + 1, nid)
            z0 = rec(b, d, depth + 1, nid)
            z1 = rec(a + b, c + d, depth + 1, nid) - z2 - z0  # (a+b)(c+d) - ac - bd
            res = z2 * p * p + z1 * p + z0
            if node:
                node["z"] = (z2, z1, z0)
        if node:
            node["result"] = res
            steps.append({"type": "return", "node": node["id"]})
        return res
 
    product = sign * rec(abs(x), abs(y), 0, None)
    return product, nodes, steps, stats
