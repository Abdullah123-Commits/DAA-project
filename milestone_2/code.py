import random, sys, os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

# CONSTANTS
DATA_DIR = "datasets"
SEED = 420
_size_rng = random.Random(SEED)
SIZES = [_size_rng.randint(101, 1000) for _ in range(10)]   # reproducible sizes
INF = float("inf")
LOG_DEPTH = 2

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


# input file gen (Q2)
def generate_datasets(folder=DATA_DIR, seed=SEED):
    rng = random.Random(seed)
    os.makedirs(folder, exist_ok=True)

    def big_int(digits):
        s = str(rng.randint(1, 9)) + "".join(rng.choice("0123456789") for _ in range(digits - 1))
        return ("-" if rng.random() < 0.5 else "") + s

    for k, n in enumerate(SIZES, start=1):
        vals = rng.sample(range(-10000, 10001), n)
        with open(os.path.join(folder, f"c_1D_{k:02d}.txt"), "w") as f:
            f.write("\n".join(map(str, vals)) + "\n")

        with open(os.path.join(folder, f"intmul_{k:02d}.txt"), "w") as f:
            f.write(big_int(n) + "\n" + big_int(n) + "\n")

    return len(SIZES) * 2


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
    if len(lines) == 2:
        return "mul", (int(lines[0]), int(lines[1]))
    return "1d", [_num(ln) for ln in lines]


# algorithms (Q3)
def closest_pair_1d(values):
    nums = sorted(values)
    steps = []

    def rec(lo, hi):
        size = hi - lo + 1
        if size < 2:                       # FIX: was `size > 2`
            return INF, None

        if size == 2:
            best = (nums[hi] - nums[lo], (nums[lo], nums[hi]))
            steps.append({"type": "base", "lo": lo, "hi": hi, "best": best,
                          "text": f"Base case [{lo}..{hi}]: {nums[lo]}, {nums[hi]} -> d = {best[0]}"})
            return best

        mid = (lo + hi) // 2
        steps.append({"type": "divide", "lo": lo, "hi": hi, "mid": mid,
                      "text": f"Divide [{lo}..{hi}] ({size} numbers) between index {mid} and {mid + 1}"})

        left = rec(lo, mid)
        right = rec(mid + 1, hi)
        cross = (nums[mid + 1] - nums[mid], (nums[mid], nums[mid + 1]))
        best = min(left, right, cross, key=lambda t: t[0])
        steps.append({"type": "combine", "lo": lo, "hi": hi, "mid": mid, "best": best,
                      "text": f"Combine [{lo}..{hi}]: left d = {left[0]}, right d = {right[0]}, "
                              f"cross d = {cross[0]} -> best d = {best[0]}"})
        return best

    d, pair = rec(0, len(nums) - 1) if len(nums) >= 2 else (INF, None)
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


def sh(n, keep=4):
    s = str(n)
    # FIX: condition was inverted (short numbers were being abbreviated)
    return s if len(s) <= 2 * keep + 3 else f"{s[:keep]}...{s[-keep:]}({len(s.lstrip('-'))}d)"


THEMES = {
    "light": dict(
        bg="#f5f6fa", fg="#1e2430", panel="#ffffff", border="#dfe3ea",
        accent="#2563eb", accent_hover="#1d4ed8", muted="#6b7280",
        node_default="#e8eefc", node_active="#fde68a", node_done="#bbf7d0",
        node_edge="#64748b", line="#cbd5e1", point="#94a3b8", point_in="#2563eb",
        pair="#dc2626", region="#eff6ff", split="#cc6600",
    ),
    "dark": dict(
        bg="#0f172a", fg="#e2e8f0", panel="#1e293b", border="#334155",
        accent="#3b82f6", accent_hover="#60a5fa", muted="#94a3b8",
        node_default="#1e3a5f", node_active="#a16207", node_done="#166534",
        node_edge="#94a3b8", line="#475569", point="#64748b", point_in="#60a5fa",
        pair="#f87171", region="#172554", split="#fb923c",
    )
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DAA Project - Visualizer")
        self.geometry("1280x920")
        self.minsize(1000, 600)

        self.steps, self.kind, self.ctx, self.job = [], None, None, None
        self.i = 0                                   # FIX: was never initialised
        self.speed_ms = 170
        self.theme_name = "light"
        self.colors = THEMES[self.theme_name]

        self._build_style()
        self._build_header()
        self._build_toolbar()                        # FIX: method was named build_toolbar
        self._build_body()
        self._build_statusbar()

        self.bind("<Key-space>", lambda e: self.play())
        self.bind("<Right>", lambda e: self.go(1))
        self.bind("<Left>", lambda e: self.go(-1))
        self.bind("<Home>", lambda e: self.go(-10**9))
        self.bind("<End>", lambda e: self.go(10**9))
        self.bind("<Control-o>", lambda e: self.open())
        self.bind("<F11>", lambda e: self.toggle_theme())

        self.apply_theme()

    def _build_style(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

    def _build_header(self):
        self.header = tk.Frame(self, height=52)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        self.title_lbl = tk.Label(self.header, text="  Divide & Conquer Visualizer",
                                  font=("Segoe UI", 15, "bold"), anchor="w")
        self.title_lbl.pack(side="left", padx=(12, 0))        # FIX: was packed twice

        self.subtitle = tk.Label(self.header, text="CS302 · closest pair & karatsuba",
                                 font=("Segoe UI", 10), anchor="w")
        self.subtitle.pack(side="left", padx=(12, 0))

        # FIX: theme_btn was used in apply_theme but never created
        self.theme_btn = tk.Button(self.header, text="🌓", command=self.toggle_theme,
                                   relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 11))
        self.theme_btn.pack(side="right", padx=(0, 12))

        self.file_lbl = tk.Label(self.header, text="No file loaded",
                                 font=("Segoe UI", 10, "italic"), anchor="e")
        self.file_lbl.pack(side="right", padx=12)

    def _build_toolbar(self):
        self.toolbar = tk.Frame(self)
        self.toolbar.pack(fill="x", side="top", padx=10, pady=(0, 6))

        def btn(text, cmd, **kw):
            b = tk.Button(self.toolbar, text=text, command=cmd, relief="flat",
                          font=("Segoe UI", 10), padx=10, pady=5, cursor="hand2", bd=0, **kw)
            b.pack(side="left", padx=3)
            return b

        self.open_btn = btn("📂  Open", self.open)
        self.start_btn = btn("⏮⏮", lambda: self.go(-10**9))
        self.back_btn = btn("◀", lambda: self.go(-1))
        self.next_btn = btn("▶", lambda: self.go(1))
        self.step25_btn = btn("+25", lambda: self.go(25))
        self.play_btn = btn("▶  Play", self.play)
        self.end_btn = btn("⏭", lambda: self.go(10**9))
        self.reset_btn = btn("↺  Reset", lambda: self.go(-10**9))

        tk.Label(self.toolbar, text="Speed:", font=("Segoe UI", 10)).pack(side="left", padx=(16, 4))
        self.speed_var = tk.DoubleVar(value=650)       # higher = faster
        self.speed_scale = ttk.Scale(self.toolbar, from_=20, to=800, orient="horizontal",
                                     variable=self.speed_var, length=120, command=self._on_speed)
        self.speed_scale.pack(side="left")

        self.progress = ttk.Progressbar(self.toolbar, length=200, mode="determinate")
        self.progress.pack(side="right", padx=(0, 10))
        self.step_lbl = tk.Label(self.toolbar, text="0 / 0", font=("Segoe UI", 10))
        self.step_lbl.pack(side="right", padx=(0, 8))

    def _build_body(self):
        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        paned = ttk.Panedwindow(body, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # canvas
        left = tk.Frame(paned)
        paned.add(left, weight=3)
        self.canvas_frame = tk.Frame(left, bd=0, highlightthickness=1)
        self.canvas_frame.pack(fill="both", expand=True)
        self.cv = tk.Canvas(self.canvas_frame, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.draw())

        # log
        right = tk.Frame(paned)
        paned.add(right, weight=2)

        log_head = tk.Frame(right)
        log_head.pack(fill="x")
        tk.Label(log_head, text="  Execution log", font=("Segoe UI", 11, "bold"),
                 anchor="w").pack(side="left", pady=4)
        self.log_count = tk.Label(log_head, text="", font=("Segoe UI", 9), anchor="e")
        self.log_count.pack(side="right", padx=8)

        self.log_frame = tk.Frame(right, bd=0, highlightthickness=1)
        self.log_frame.pack(fill="both", expand=True, pady=(4, 0))
        self.log = tk.Text(self.log_frame, font=("Consolas", 10), wrap="word",
                           relief="flat", bd=0, padx=8, pady=6)
        self.log.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(self.log_frame, command=self.log.yview)
        sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=sb.set, state="disabled")

    def _build_statusbar(self):
        self.status = tk.Frame(self, height=26)
        self.status.pack(fill="x", side="bottom")
        self.status.pack_propagate(False)

        self.info = tk.Label(self.status, text="Open an input file to begin",
                             font=("Segoe UI", 9), anchor="w")
        self.info.pack(side="left", padx=12)

        self.hint = tk.Label(self.status,
                             text="Space: play/pause · ←/→: step · Ctrl+O: open · F11: theme",
                             font=("Segoe UI", 9), anchor="e")
        self.hint.pack(side="right", padx=12)

    def toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.colors = THEMES[self.theme_name]
        self.apply_theme()

    def apply_theme(self):
        c = self.colors
        self.configure(bg=c["bg"])
        for w in (self.header, self.toolbar):
            w.configure(bg=c["bg"])
        self.title_lbl.configure(bg=c["bg"], fg=c["fg"])
        self.subtitle.configure(bg=c["bg"], fg=c["muted"])
        self.file_lbl.configure(bg=c["bg"], fg=c["accent"])
        self.theme_btn.configure(bg=c["bg"], fg=c["fg"], activebackground=c["bg"])

        for w in self.toolbar.winfo_children():
            try:
                if isinstance(w, tk.Label):
                    w.configure(bg=c["bg"], fg=c["fg"])
                if isinstance(w, tk.Button):
                    w.configure(bg=c["accent"], fg="white",
                                activebackground=c["accent_hover"], activeforeground="white")
            except tk.TclError:
                pass

        self.canvas_frame.configure(bg=c["border"], highlightbackground=c["border"])
        self.cv.configure(bg=c["panel"])
        self.log_frame.configure(bg=c["border"], highlightbackground=c["border"])
        self.log.configure(bg=c["panel"], fg=c["fg"], insertbackground=c["fg"],
                           selectbackground=c["accent"], selectforeground="white")
        self.log.tag_configure("title", foreground=c["accent"], font=("Consolas", 10, "bold"))
        self.log.tag_configure("fade", foreground=c["muted"])

        self.status.configure(bg=c["panel"])
        self.info.configure(bg=c["panel"], fg=c["fg"])
        self.hint.configure(bg=c["panel"], fg=c["muted"])

        self.style.configure("TScale", background=c["bg"], troughcolor=c["border"])
        self.style.configure("Horizontal.TProgressbar", background=c["accent"], troughcolor=c["border"])
        self.draw()

    def _on_speed(self, _=None):
        # slider right = faster = shorter delay
        self.speed_ms = max(20, int(820 - self.speed_var.get()))

    # ---------- actions ----------
    def open(self):
        path = filedialog.askopenfilename(
            initialdir=DATA_DIR if os.path.isdir(DATA_DIR) else ".",
            filetypes=[("Text files", "*.txt")])
        if not path:
            return
        try:
            kind, data = load_file(path)
            self.stop()
            if kind == "mul":
                prod, ctx, steps, st = karatsuba_multiply(*data)
                res = (f"{len(str(abs(prod)))} digits · correct = {prod == data[0] * data[1]} "
                       f"· calls = {st['calls']}")
            else:
                d, pair, steps, ctx = closest_pair_1d(data)
                res = f"closest pair {pair} · d = {d}"
                steps.append({"type": "done", "best": (d, pair), "text": f"DONE: {res}"})
        except Exception as e:
            messagebox.showerror("Failed to load", str(e))
            return

        self.kind, self.ctx, self.steps = kind, ctx, steps
        self.i = 0
        self.file_lbl.config(text=os.path.basename(path))
        self.info.config(text=res)
        self.progress["maximum"] = max(1, len(self.steps) - 1)
        self.show()

    def go(self, k):
        if self.steps:
            self.i = max(0, min(len(self.steps) - 1, self.i + k))
            self.show()

    def play(self):
        if not self.steps:
            return
        if self.job:
            self.stop()
        else:
            if self.i >= len(self.steps) - 1:            # restart if already at the end
                self.i = 0
            self.play_btn.configure(text="⏸  Pause")
            self.tick()

    def tick(self):
        if self.i < len(self.steps) - 1:
            self.go(1)
            self.job = self.after(self.speed_ms, self.tick)
        else:
            self.job = None
            self.play_btn.configure(text="▶  Play")

    def stop(self):
        if self.job:
            self.after_cancel(self.job)
            self.job = None
        self.play_btn.configure(text="▶  Play")

    # ---------- rendering ----------
    def text(self, s):
        if "node" not in s:
            return s.get("text", "")
        n = self.ctx[s["node"]]
        pad = "  " * n["depth"]
        if s["type"] == "call":
            t = f"{pad}CALL {sh(n['x'])} × {sh(n['y'])}"
            if n["split"]:
                m, a, b, cc, d = n["split"]
                t += f"\n{pad}  split 10^{m}: a={sh(a)} b={sh(b)} c={sh(cc)} d={sh(d)}"
            return t
        t = f"{pad}RETURN {sh(n['result'])}"
        if n["z"]:
            t += f"\n{pad}  ac={sh(n['z'][0])} bd={sh(n['z'][2])} mid={sh(n['z'][1])}"
        return t

    def show(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        lo = max(0, self.i - 10)
        for k, s in enumerate(self.steps[lo:self.i + 1]):
            tag = "title" if k == self.i - lo else "fade"
            self.log.insert("end", self.text(s) + "\n\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")
        self.log_count.config(text=f"{self.i + 1}/{len(self.steps)}")
        self.step_lbl.config(text=f"{self.i + 1} / {len(self.steps)}")
        self.progress["value"] = self.i
        self.draw()

    def draw(self):
        cv = self.cv
        W, H = cv.winfo_width(), cv.winfo_height()
        cv.delete("all")
        c = self.colors
        if W < 10:
            return
        if not self.steps:
            cv.create_text(W / 2, H / 2, text="Open a file to start",
                           font=("Segoe UI", 12), fill=c["muted"])
            return

        s = self.steps[self.i]
        head = self.text(s).split("\n")[0]
        cv.create_text(14, 10, anchor="nw", font=("Segoe UI", 11, "bold"),
                       text=head, fill=c["fg"])
        if self.kind == "mul":
            self.draw_tree(s, W)
        elif self.kind == "1d":
            self.draw_1d(s, W, H)

    def draw_1d(self, s, W, H):
        cv, c = self.cv, self.colors
        nums, y = self.ctx, H / 2 + 10
        mn, mx = nums[0], nums[-1]
        span = (mx - mn) or 1
        X = lambda v: 40 + (v - mn) / span * (W - 80)

        cv.create_line(30, y, W - 30, y, fill=c["line"], width=2)
        inside = range(s["lo"], s["hi"] + 1) if "lo" in s else ()
        if inside:
            cv.create_rectangle(X(nums[s["lo"]]) - 6, y - 90,
                                X(nums[s["hi"]]) + 6, y + 90,
                                fill=c["region"], outline=c["border"])

        for i, v in enumerate(nums):
            col = c["point_in"] if i in inside else c["point"]
            r = 4 if i in inside else 2.5
            cv.create_oval(X(v) - r, y - r, X(v) + r, y + r, fill=col, outline="")

        if "mid" in s:
            xm = (X(nums[s["mid"]]) + X(nums[s["mid"] + 1])) / 2
            cv.create_line(xm, y - 100, xm, y + 100, fill=c["split"], dash=(5, 4), width=2)
            cv.create_text(xm, y - 108, text="split", fill=c["split"],
                           font=("Segoe UI", 9, "italic"))

        if s.get("best") and s["best"][1]:
            a, b = s["best"][1]
            cv.create_line(X(a), y - 30, X(b), y - 30, fill=c["pair"], width=3)
            for v in (a, b):
                cv.create_oval(X(v) - 7, y - 7, X(v) + 7, y + 7,
                               fill=c["pair"], outline="white", width=2)
            cv.create_text((X(a) + X(b)) / 2, y - 48, fill=c["pair"],
                           text=f"d = {s['best'][0]}",
                           font=("Segoe UI", 10, "bold"))

        cv.create_text(14, H - 12, anchor="w", fill=c["muted"],
                       font=("Segoe UI", 9), text=f"n = {len(nums)}  ·  min = {mn}  ·  max = {mx}")

    def draw_tree(self, s, W):
        cv, c = self.cv, self.colors
        seen = [t for t in self.steps[: self.i + 1] if "node" in t]
        called = {t["node"] for t in seen if t["type"] == "call"}
        done = {t["node"] for t in seen if t["type"] == "return"}
        active = s.get("node")

        pos = {}
        for d in range(LOG_DEPTH + 1):
            row = [n for n in self.ctx if n["depth"] == d]
            for k, n in enumerate(row):
                pos[n["id"]] = ((k + 0.5) / len(row) * W,
                                80 + d * 150,
                                max(60, W / len(row) / 2 - 8))

        for n in self.ctx:
            if n["id"] in called:
                for ch in n["children"]:
                    if ch in called:
                        cv.create_line(*pos[n["id"]][:2], *pos[ch][:2],
                                       fill=c["line"], width=2)

        digits = lambda v: len(str(abs(v)))
        for n in self.ctx:
            if n["id"] not in called:
                continue
            x, y, hw = pos[n["id"]]
            fill = (c["node_active"] if n["id"] == active
                    else c["node_done"] if n["id"] in done
                    else c["node_default"])
            cv.create_rectangle(x - hw, y - 34, x + hw, y + 34,
                                fill=fill, outline=c["node_edge"],
                                width=2 if n["id"] == active else 1)
            label = (f"x: {digits(n['x'])}d   y: {digits(n['y'])}d\n"
                     + (f"= {digits(n['result'])}d" if n["id"] in done else "working…"))
            cv.create_text(x, y, font=("Consolas", 9), text=label, fill=c["fg"])


if __name__ == "__main__":
    if not os.path.isdir(DATA_DIR):
        generate_datasets()
    App().mainloop()