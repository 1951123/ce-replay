#!/usr/bin/env python3
"""Characterize PostgreSQL 16 functional-dependency selectivity semantics."""

from __future__ import annotations

import argparse
import itertools
import json
import re
from pathlib import Path

import psycopg


RAW_RE = re.compile(r" rows=([^ ]+)")
FIELD_RE = re.compile(r"([a-z_]+)=([^ ]+)")
ATTNUM = {"a": 1, "b": 2, "c": 3, "d": 4, "flag": 5, "txt": 6}
CANDIDATES = {
    "ab": ("a", "b"),
    "abc": ("a", "b", "c"),
    "cd": ("c", "d"),
}


def as_text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


def fields(message: str) -> dict[str, str]:
    return dict(FIELD_RE.findall(message))


def parse_dependencies(text: str) -> list[dict]:
    # pg_dependencies_out emits JSON-shaped text and preserves payload order.
    obj = json.loads(text)
    result = []
    for key, degree in obj.items():
        left, right = key.split(" => ")
        attrs = [int(x.strip()) for x in left.split(",")] + [int(right)]
        result.append({"attributes": attrs, "degree": float(degree)})
    return result


def strongest(payloads: list[list[dict]], available: set[int]):
    winner = None
    for payload in payloads:
        for dep in payload:
            attrs = dep["attributes"]
            if len(attrs) > len(available) or not set(attrs) <= available:
                continue
            if winner is not None:
                if len(attrs) < len(winner["attributes"]):
                    continue
                if len(attrs) == len(winner["attributes"]) and winner["degree"] > dep["degree"]:
                    continue
            winner = dep                 # exact ties deliberately choose last
    return winner


def replay(payloads: list[list[dict]], simple: dict[int, float]):
    available = set(simple)
    chosen = []
    while True:
        dep = strongest(payloads, available)
        if dep is None:
            break
        chosen.append(dep)
        available.remove(dep["attributes"][-1])

    used = {a for dep in chosen for a in dep["attributes"]}
    sels = {a: simple[a] for a in used}
    for dep in reversed(chosen):
        determinant = 1.0
        for a in dep["attributes"][:-1]:
            determinant *= sels[a]
        implied = dep["attributes"][-1]
        s2, degree = sels[implied], dep["degree"]
        if determinant <= s2:
            sels[implied] = degree + (1.0 - degree) * s2
        else:
            sels[implied] = degree * s2 / determinant + (1.0 - degree) * s2
    value = 1.0
    for sel in sels.values():
        value *= sel
    return value, chosen


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="/tmp")
    ap.add_argument("--port", type=int, default=55432)
    ap.add_argument("--user", default="postgres")
    ap.add_argument("--db", default="census")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    conn = psycopg.connect(host=args.host, port=args.port, user=args.user,
                           dbname=args.db, autocommit=True)
    cur = conn.cursor()
    notices: list[str] = []
    conn.add_notice_handler(lambda d: notices.append(d.message_primary))

    def execute(sql, params=None):
        notices.clear()
        cur.execute(sql, params)
        return list(notices)

    def explain(where):
        msgs = execute(f"EXPLAIN SELECT * FROM fd_sem_v0 WHERE {where}")
        raw = [m for m in msgs if m.startswith("CE_REPLAY_RAW_ROWS")]
        if len(raw) != 1:
            raise RuntimeError((where, raw, msgs))
        return float(RAW_RE.search(raw[0]).group(1)), msgs

    def drop_stats():
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid='fd_sem_v0'::regclass")
        for (name,) in cur.fetchall():
            cur.execute(f'DROP STATISTICS IF EXISTS "{as_text(name)}"')

    try:
        cur.execute("DROP TABLE IF EXISTS fd_sem_v0")
        cur.execute("CREATE TABLE fd_sem_v0(a int,b int,c int,d int,flag boolean,txt text)")
        cur.execute("""
            INSERT INTO fd_sem_v0
            SELECT a,b,c, CASE WHEN a<60 THEN c ELSE rep%50 END AS d,
                   (a%2=0), 'v'||a
            FROM (
              SELECT a,b,rep, CASE WHEN a<80 THEN b ELSE rep%100 END AS c
              FROM (
                SELECT a,rep, CASE WHEN a<90 THEN a ELSE rep%100 END AS b
                FROM generate_series(0,99) a CROSS JOIN generate_series(0,999) rep
              ) ab
            ) abc
        """)
        cur.execute("ALTER TABLE fd_sem_v0 ALTER a SET STATISTICS 10000")
        cur.execute("ALTER TABLE fd_sem_v0 ALTER b SET STATISTICS 10000")
        cur.execute("ALTER TABLE fd_sem_v0 ALTER c SET STATISTICS 10000")
        cur.execute("ALTER TABLE fd_sem_v0 ALTER d SET STATISTICS 10000")

        # Build one canonical payload per candidate from the same ANALYZE sample.
        for cid, cols in CANDIDATES.items():
            cur.execute(f"CREATE STATISTICS fdv0_tpl_{cid} (dependencies) ON {','.join(cols)} FROM fd_sem_v0")
            cur.execute(f"ALTER STATISTICS fdv0_tpl_{cid} SET STATISTICS 10000")
        cur.execute("ANALYZE fd_sem_v0")
        payload_text = {}
        cur.execute("CREATE TEMP TABLE fdv0_payload_backup(cid text PRIMARY KEY, payload pg_dependencies)")
        for cid in CANDIDATES:
            cur.execute("SELECT d.stxddependencies, d.stxddependencies::text "
                        "FROM pg_statistic_ext s JOIN pg_statistic_ext_data d ON d.stxoid=s.oid "
                        "WHERE s.stxname=%s AND NOT d.stxdinherit", (f"fdv0_tpl_{cid}",))
            binary, text = cur.fetchone()
            payload_text[cid] = as_text(text)
            if binary is None:
                raise RuntimeError(f"empty dependency payload for {cid}")
            cur.execute("INSERT INTO fdv0_payload_backup "
                        "SELECT %s, d.stxddependencies FROM pg_statistic_ext s "
                        "JOIN pg_statistic_ext_data d ON d.stxoid=s.oid "
                        "WHERE s.stxname=%s AND NOT d.stxdinherit",
                        (cid, f"fdv0_tpl_{cid}"))
        drop_stats()

        total_rows, _ = explain("TRUE")
        clauses = {"a": "a=7", "b": "b=7", "c": "c=7", "d": "d=3"}
        simple = {ATTNUM[k]: explain(v)[0] / total_rows for k, v in clauses.items()}
        full_where = " AND ".join(clauses.values())

        def install(order):
            drop_stats()
            oids = {}
            for cid in order:
                cols = CANDIDATES[cid]
                name = f"fdv0_run_{cid}"
                cur.execute(f"CREATE STATISTICS {name} (dependencies) ON {','.join(cols)} FROM fd_sem_v0")
                cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s", (name,))
                oid = int(cur.fetchone()[0]); oids[cid] = oid
            # CREATE STATISTICS does not create pg_statistic_ext_data rows.
            if order:
                cur.execute("ANALYZE fd_sem_v0")
            for cid, oid in oids.items():
                cur.execute("UPDATE pg_statistic_ext_data d SET stxddependencies=b.payload "
                            "FROM fdv0_payload_backup b "
                            "WHERE d.stxoid=%s AND NOT d.stxdinherit AND b.cid=%s",
                            (oid, cid))
            return oids

        scenarios = []
        orders = []
        ids = list(CANDIDATES)
        for n in range(4):
            orders.extend(itertools.combinations(ids, n))
        orders.extend(itertools.permutations(ids))
        seen = set()
        for order in orders:
            label = ",".join(order) or "none"
            if label in seen:
                continue
            seen.add(label)
            oids = install(order)
            native_rows, msgs = explain(full_where)
            native_result = [fields(m) for m in msgs if m.startswith("CE_REPLAY_FD_RESULT")]
            choose = [fields(m) for m in msgs if m.startswith("CE_REPLAY_FD_CHOOSE")]
            apply = [fields(m) for m in msgs if m.startswith("CE_REPLAY_FD_APPLY")]
            parsed = [parse_dependencies(payload_text[cid]) for cid in order]
            replay_sel, replay_chosen = replay(parsed, simple) if len(order) else (1.0, [])
            if replay_chosen:
                if not native_result:
                    raise RuntimeError({"scenario": label, "messages": msgs,
                                        "replay_chosen": replay_chosen})
                native_fd_sel = float(native_result[-1]["selectivity"])
                relerr = abs(replay_sel-native_fd_sel)/max(abs(native_fd_sel), 1e-300)
            else:
                native_fd_sel, relerr = 1.0, 0.0
            scenarios.append({"order": list(order), "oids": oids,
                              "native_rows": native_rows,
                              "native_fd_selectivity": native_fd_sel,
                              "external_fd_selectivity": replay_sel,
                              "relative_error": relerr,
                              "native_choose": choose, "native_apply": apply,
                              "external_choose": replay_chosen})

        # Applicability: isolate the AB payload and vary clause shapes.
        install(("ab",))
        applicability_sql = {
            "eq_eq": "a=7 AND b=7",
            "const_eq_var": "7=a AND b=7",
            "in_eq": "a IN (7,8) AND b=7",
            "or_same_attr_eq": "(a=7 OR a=8) AND b=7",
            "range_eq": "a>7 AND b=7",
            "neq_eq": "a<>7 AND b=7",
            "var_eq_var": "a=b AND b=7",
            "duplicate_same_attr": "a=7 AND a<20 AND b=7",
            "single_attr": "a=7",
        }
        applicability = {}
        for name, where in applicability_sql.items():
            rows, msgs = explain(where)
            applicability[name] = {"where": where, "rows": rows,
                "used_fd": any(m.startswith("CE_REPLAY_FD_RESULT") for m in msgs),
                "trace": [m for m in msgs if m.startswith("CE_REPLAY_FD_")]}

        # Expression matching is separately supported by exact expression-tree equality.
        drop_stats()
        cur.execute("CREATE STATISTICS fdv0_expr (dependencies) ON lower(txt), a FROM fd_sem_v0")
        cur.execute("ANALYZE fd_sem_v0")
        expr_cases = {}
        for name, where in {"exact": "lower(txt)='v7' AND a=7",
                            "nonmatching": "upper(txt)='V7' AND a=7"}.items():
            rows, msgs = explain(where)
            expr_cases[name] = {"where": where, "rows": rows,
                "used_fd": any(m.startswith("CE_REPLAY_FD_RESULT") for m in msgs),
                "trace": [m for m in msgs if m.startswith("CE_REPLAY_FD_")]}

        # Composition: MCV consumes a,b; FD may still consume the disjoint c,d pair.
        drop_stats()
        cur.execute("CREATE STATISTICS fdv0_mix_ab (mcv) ON a,b FROM fd_sem_v0")
        cur.execute("CREATE STATISTICS fdv0_mix_abc (dependencies) ON a,b,c FROM fd_sem_v0")
        cur.execute("CREATE STATISTICS fdv0_mix_cd (dependencies) ON c,d FROM fd_sem_v0")
        cur.execute("ANALYZE fd_sem_v0")
        mix_rows, mix_msgs = explain(full_where)
        composition = {"rows": mix_rows,
            "mcv_trace": [m for m in mix_msgs if m.startswith("CE_REPLAY_MCV")],
            "fd_trace": [m for m in mix_msgs if m.startswith("CE_REPLAY_FD_")]}

        result = {
            "experiment": "FD-Semantics-v0",
            "table_rows": int(total_rows),
            "candidates": {cid: {"columns": CANDIDATES[cid],
                                 "payload": payload_text[cid],
                                 "parsed": parse_dependencies(payload_text[cid])}
                           for cid in CANDIDATES},
            "simple_selectivities": {str(k): v for k, v in simple.items()},
            "scenarios": scenarios,
            "validation": {"count": len(scenarios),
                           "max_relative_error": max(s["relative_error"] for s in scenarios)},
            "applicability": applicability,
            "expression_applicability": expr_cases,
            "mcv_fd_composition": composition,
        }
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"validation": result["validation"],
                          "applicability": {k:v["used_fd"] for k,v in applicability.items()},
                          "expression": {k:v["used_fd"] for k,v in expr_cases.items()},
                          "composition": {"mcv_nodes": len(composition["mcv_trace"]),
                                          "fd_events": len(composition["fd_trace"])}}, indent=2))
    finally:
        drop_stats()
        cur.execute("DROP TABLE IF EXISTS fd_sem_v0")
        conn.close()


if __name__ == "__main__":
    main()
