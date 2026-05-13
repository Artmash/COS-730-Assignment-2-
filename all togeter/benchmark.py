import time
import sqlite3
import sys
from typing import List, Dict

try:
    from baseline_system import UI as BaselineUI
except ImportError:
    print("baseline_system.py not found")
    sys.exit(1)

try:
    from optimised_system import UI as OptimisedUI
except ImportError:
    print("optimised_system.py not found")
    sys.exit(1)

DB_NAME = "submission_review.db"

def reset_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.executescript("DELETE FROM reviews; DELETE FROM submissions;")
    cursor.execute("UPDATE reviewers SET current_workload = 0")
    conn.commit()
    conn.close()

def benchmark_timing(ui_class, runs=500):
    test_data = {
        "title": "AI in SE",
        "content": "Full paper content.",
        "email": "researcher@example.com",
    }
    times = []
    for _ in range(runs):
        reset_database()
        start = time.perf_counter()
        result = ui_class.submit(test_data)
        end = time.perf_counter()
        times.append(end - start)
        assert result.get("status") in {"accepted", "rejected", "revision"}
    avg = sum(times) / runs
    variance = sum((t - avg) ** 2 for t in times) / runs
    return {
        "avg": avg,
        "min": min(times),
        "max": max(times),
        "std": variance ** 0.5,
    }

def count_db_operations(ui_class):
    counter = {"n": 0}
    real_connect = sqlite3.connect

    class CountingCursor:
        def __init__(self, real_cursor):
            self._c = real_cursor
        def execute(self, sql, params=()):
            counter["n"] += 1
            return self._c.execute(sql, params)
        def executemany(self, sql, params):
            counter["n"] += 1
            return self._c.executemany(sql, params)
        def fetchall(self):
            return self._c.fetchall()
        def executescript(self, sql):
            counter["n"] += 1
            return self._c.executescript(sql)
        @property
        def lastrowid(self):
            return self._c.lastrowid

    class CountingConn:
        def __init__(self, real_conn):
            self._conn = real_conn
        def cursor(self):
            return CountingCursor(self._conn.cursor())
        def commit(self):
            return self._conn.commit()
        def close(self):
            return self._conn.close()
        def executescript(self, sql):
            counter["n"] += 1
            return self._conn.executescript(sql)

    def fake_connect(db_name):
        return CountingConn(real_connect(db_name))

    import baseline_system as base_mod
    import optimised_system as opt_mod
    base_mod.sqlite3.connect = fake_connect
    opt_mod.sqlite3.connect = fake_connect

    reset_database()
    result = ui_class.submit({
        "title": "AI in SE",
        "content": "Full paper content.",
        "email": "x@example.com",
    })
    base_mod.sqlite3.connect = real_connect
    opt_mod.sqlite3.connect = real_connect
    return counter["n"]

def count_method_calls(ui_class):
    counter = {"n": 0}
    def tracer(frame, event, arg):
        if event == "call":
            counter["n"] += 1
        return tracer
    reset_database()
    sys.settrace(tracer)
    ui_class.submit({
        "title": "AI in SE",
        "content": "Full paper content.",
        "email": "x@example.com",
    })
    sys.settrace(None)
    return counter["n"]

def get_cyclomatic_complexity(filepath):
    try:
        from radon.complexity import cc_visit
        with open(filepath, "r") as f:
            code = f.read()
        return sum(item.complexity for item in cc_visit(code))
    except ImportError:
        with open(filepath, "r") as f:
            code = f.read()
        keywords = ["if ", "elif ", "else:", "for ", "while ", " and ", " or "]
        return sum(code.count(kw) for kw in keywords)

def main():
    RUNS = 500
    print(f"\n=== Empirical Evaluation ({RUNS} runs) ===\n")

    print("Benchmarking baseline...")
    b_time = benchmark_timing(BaselineUI, RUNS)
    print("Benchmarking optimised...")
    o_time = benchmark_timing(OptimisedUI, RUNS)

    print("\n--- Execution Time (ms) ---")
    print(f"Average:  baseline {b_time['avg']*1000:.3f} ms, optimised {o_time['avg']*1000:.3f} ms, improvement {((1 - o_time['avg']/b_time['avg'])*100):.1f}%")
    print(f"Min:      {b_time['min']*1000:.3f} / {o_time['min']*1000:.3f}")
    print(f"Max:      {b_time['max']*1000:.3f} / {o_time['max']*1000:.3f}")
    print(f"Std dev:  {b_time['std']*1000:.3f} / {o_time['std']*1000:.3f}")

    print("\n--- Method Calls ---")
    b_calls = count_method_calls(BaselineUI)
    o_calls = count_method_calls(OptimisedUI)
    print(f"Baseline: {b_calls}, Optimised: {o_calls} ({(1 - o_calls/b_calls)*100:.1f}% fewer)")

    print("\n--- Database Operations ---")
    b_db = count_db_operations(BaselineUI)
    o_db = count_db_operations(OptimisedUI)
    print(f"Baseline: {b_db} SQL ops, Optimised: {o_db} SQL ops ({(1 - o_db/b_db)*100:.1f}% fewer)")

    print("\n--- Cyclomatic Complexity ---")
    b_cc = get_cyclomatic_complexity("baseline_system.py")
    o_cc = get_cyclomatic_complexity("optimised_system.py")
    print(f"Baseline: {b_cc}, Optimised: {o_cc} ({(1 - o_cc/b_cc)*100:.1f}% reduction)")

    print("\n--- Trade-offs ---")
    print("+ Lower coupling, centralised rules, batch DB writes, workload tracking.")
    print("- Slight increase in classes (repository, coordinator, engine).")
    print("- Workload update adds a second batch DB operation (negligible).")

if __name__ == "__main__":
    main()