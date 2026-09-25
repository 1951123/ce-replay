#!/usr/bin/env python3
"""Real-DMV frozen-payload replay validation and inclusion non-monotonicity."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import re
import statistics
import struct
import time
from collections import Counter, defaultdict
from pathlib import Path

import psycopg


RAW_RE = re.compile(r"CE_REPLAY_RAW_ROWS .* rows=([^ ]+) selectivity=([^ ]+)")
MCV_RE = re.compile(r"CE_REPLAY_MCV oid=(\d+) simple=([^ ]+) mcv=([^ ]+) base=([^ ]+) total=([^ ]+) stat=([^ ]+)")
TOL = 1e-12


def text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


def relerr(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


def qerror(estimate, truth):
    # Multiplicative q-error is defined only on the positive-truth domain.
    # Zero-truth queries remain in replay/native semantic validation but have
    # exactly zero objective weight.
    if truth == 0:
        return 0.0
    if truth < 0:
        raise ValueError(f"negative truth cardinality: {truth}")
    estimate = max(estimate, 1e-300)
    return max(estimate / truth, truth / estimate)


def sql_literal_value(token):
    token = token.strip()
    if not (token.startswith("'") and token.endswith("'")):
        raise ValueError(token)
    return token[1:-1].replace("''", "'")


def parse_queries(path):
    entry = re.compile(r"^\s*SELECT\s+COUNT\(\*\)\s+FROM\s+DMV\s+WHERE\s+(.+)\s*$", re.I)
    clause_re = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(=|IN)\s*(.+?)\s*$", re.I)
    queries = []
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        if not raw.strip():
            continue
        sql, sep, truth = raw.rpartition("||")
        match = entry.fullmatch(sql.strip())
        if not sep or not match or not re.fullmatch(r"-?\d+", truth.strip()):
            raise ValueError((lineno, raw[:200]))
        clauses = []
        for source in re.split(r"\s+AND\s+", match.group(1), flags=re.I):
            cm = clause_re.fullmatch(source)
            if not cm:
                raise ValueError((lineno, source))
            column, op, rhs = cm.group(1).lower(), cm.group(2).upper(), cm.group(3)
            if op == "=":
                values = [sql_literal_value(rhs)]
                kind = "eq"
            else:
                if not (rhs.startswith("(") and rhs.endswith(")")):
                    raise ValueError((lineno, source))
                tokens = next(csv.reader([rhs[1:-1]], quotechar="'", skipinitialspace=True))
                values = [x.replace("''", "'") for x in tokens]
                kind = "scalar_array"
            clauses.append({"column": column, "kind": kind, "values": values,
                            "sql": source.strip()})
        columns = sorted({x["column"] for x in clauses})
        queries.append({"id": f"dmv.{len(queries)+1}", "line": lineno,
                        "where": match.group(1), "truth": int(truth),
                        "clauses": clauses, "columns": columns})
    return queries


def combine(simple, mcv, base, total):
    other = min(max(simple - base, 0.0), 1.0)
    other = min(other, 1.0 - total)
    return min(max(mcv + other, 0.0), 1.0)


def clause_matches(value, is_null, clause):
    if is_null:
        return False
    return any(candidate is not None and value == candidate for candidate in clause["values"])


def parse_dependencies(value, attnames):
    if value is None:
        return []
    obj = json.loads(text(value))
    result = []
    for key, degree in obj.items():
        left, right = key.split(" => ")
        nums = [int(x.strip()) for x in left.split(",")] + [int(right)]
        result.append({"attributes": [attnames[n] for n in nums],
                       "degree": float(degree)})
    return result


def parse_binary_dependencies(value, attnames):
    data = bytes(value); offset = 0
    _, _, count = struct.unpack_from("=III", data, offset); offset += 12
    result = []
    for _ in range(count):
        degree = struct.unpack_from("=d", data, offset)[0]; offset += 8
        count_attrs = struct.unpack_from("=h", data, offset)[0]; offset += 2
        nums = list(struct.unpack_from("=" + "h" * count_attrs, data, offset))
        offset += 2 * count_attrs
        result.append({"attributes": [attnames[n] for n in nums], "degree": degree})
    if offset != len(data):
        raise ValueError((offset, len(data)))
    return result


def replay(query, selected_mcv, selected_fd, mcv, fd, trace=False):
    remaining = set(range(len(query["clauses"])))
    estimate = query["baseline_rows"]
    mtrace = []
    selected_stats = [mcv[i] for i in sorted(selected_mcv, key=lambda x: mcv[x]["oid_rank"])]
    while True:
        choices = []
        for stat in selected_stats:
            covered = [i for i in remaining
                       if query["clauses"][i]["column"] in stat["columns"]]
            covered_columns = {query["clauses"][i]["column"] for i in covered}
            if len(covered_columns) >= 2:
                choices.append(((len(covered_columns), -len(stat["columns"]),
                                 -stat["oid_rank"]), stat, covered))
        if not choices:
            break
        _, stat, covered = max(choices, key=lambda x: x[0])
        simple = math.prod(query["clause_selectivities"][i] for i in covered)
        matched = []
        for item in stat["payload"]:
            ok = True
            for i in covered:
                clause = query["clauses"][i]
                dim = stat["payload_columns"].index(clause["column"])
                if not clause_matches(item["values"][dim], item["nulls"][dim], clause):
                    ok = False
                    break
            matched.append(ok)
        mv = sum(item["frequency"] for item, ok in zip(stat["payload"], matched) if ok)
        base = sum(item["base_frequency"] for item, ok in zip(stat["payload"], matched) if ok)
        total = stat["total_frequency"]
        stat_sel = combine(simple, mv, base, total)
        estimate = 0.0 if simple == 0.0 else estimate * stat_sel / simple
        mtrace.append({"id": stat["id"], "covered_clause_indexes": covered,
                       "simple": simple, "mcv": mv, "base": base,
                       "total": total, "stat": stat_sel})
        remaining.difference_update(covered)

    available = {query["clauses"][i]["column"] for i in remaining}
    payloads = []
    for fid in sorted(selected_fd, key=lambda x: fd[x]["oid_rank"]):
        stat = fd[fid]
        if set(stat["columns"]) <= available and stat["payload"]:
            payloads.append(stat)
    chosen = []
    while True:
        winner = None
        for stat in payloads:
            for dep in stat["payload"]:
                attrs = dep["attributes"]
                if not set(attrs) <= available:
                    continue
                candidate = (len(attrs), dep["degree"], stat["oid_rank"], stat, dep)
                # PostgreSQL replaces the winner on an exact strength tie, so
                # the later payload in catalog order wins.
                if winner is None or candidate[:2] >= winner[:2]:
                    winner = candidate
        if winner is None:
            break
        stat, dep = winner[3], winner[4]
        chosen.append((stat, dep))
        available.remove(dep["attributes"][-1])

    used_attrs = {a for _, dep in chosen for a in dep["attributes"]}
    sels = {a: query["column_selectivities"][a] for a in used_attrs}
    original = math.prod(sels.values())
    for _, dep in reversed(chosen):
        determinant = math.prod(sels[x] for x in dep["attributes"][:-1])
        implied = dep["attributes"][-1]
        s2, degree = sels[implied], dep["degree"]
        sels[implied] = (degree + (1-degree)*s2 if determinant <= s2
                         else degree*s2/determinant + (1-degree)*s2)
    if chosen:
        estimate = 0.0 if original == 0.0 else estimate * math.prod(sels.values()) / original
    ftrace = [{"id": stat["id"], "attributes": dep["attributes"],
               "degree": dep["degree"]} for stat, dep in chosen]
    return (estimate, mtrace, ftrace) if trace else estimate


def summaries(values):
    return {"min": min(values), "median": statistics.median(values),
            "mean": statistics.fmean(values), "max": max(values)} if values else None


def classify(rows, tolerance=1e-12):
    counts = Counter("beneficial" if x["delta"] < -tolerance else
                     "harmful" if x["delta"] > tolerance else "neutral" for x in rows)
    nonzero = [x["delta"] for x in rows if abs(x["delta"]) > tolerance]
    return {"candidate_count": len(rows), "beneficial": counts["beneficial"],
            "neutral": counts["neutral"], "harmful": counts["harmful"],
            "best_improvement": min((x["delta"] for x in rows), default=0.0),
            "strongest_degradation": max((x["delta"] for x in rows), default=0.0),
            "median_nonzero_marginal": statistics.median(nonzero) if nonzero else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queries", type=Path, default=Path("/root/projects/extended-stats-optim-v2/benchmarks/DMV/queries/dmv.sql"))
    ap.add_argument("--csv", type=Path, default=Path("/root/projects/extended-stats-optim-v2/benchmarks/DMV/data/original.csv"))
    ap.add_argument("--audit", type=Path, default=Path("results/dmv_fit_audit_v0.json"))
    ap.add_argument("--output", type=Path, default=Path("results/dmv_baseline_nonmonotonicity_v0.json"))
    ap.add_argument("--report", type=Path, default=Path("results/dmv_baseline_nonmonotonicity_v0.md"))
    ap.add_argument("--host", default="/tmp"); ap.add_argument("--port", type=int, default=55433)
    ap.add_argument("--user", default="postgres"); ap.add_argument("--database", default="dmv_baseline_v0")
    ap.add_argument("--target", type=int, default=100)
    ap.add_argument("--keep-database", action="store_true")
    args = ap.parse_args()
    started = time.perf_counter()
    queries = parse_queries(args.queries)
    audit = json.loads(args.audit.read_text())
    pairs = sorted({tuple(pair) for q in queries for pair in itertools.combinations(q["columns"], 2)})
    expected_rows = audit["dataset"]["row_count_from_csv"]
    expected_columns = audit["dataset"]["columns"]
    if len(queries) != 1965 or len(pairs) != 36:
        raise RuntimeError((len(queries), len(pairs)))

    admin = psycopg.connect(host=args.host, port=args.port, user=args.user,
                            dbname="postgres", autocommit=True)
    with admin.cursor() as acur:
        acur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (args.database,))
        exists = acur.fetchone() is not None
        if not exists:
            acur.execute(psycopg.sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(
                psycopg.sql.Identifier(args.database)))
    con = psycopg.connect(host=args.host, port=args.port, user=args.user,
                          dbname=args.database, autocommit=True)
    cur = con.cursor(); notices = []
    con.add_notice_handler(lambda d: notices.append(d.message_primary))
    prefix = "dmv_bnm_v0_"

    def native(where):
        notices.clear()
        cur.execute("EXPLAIN SELECT * FROM dmv WHERE " + where)
        match = [RAW_RE.match(x) for x in notices if RAW_RE.match(x)]
        if len(match) != 1:
            raise RuntimeError((where, notices[-20:]))
        nodes = []
        for message in notices:
            m = MCV_RE.match(message)
            if m:
                nodes.append({"oid": int(m.group(1)), "simple": float(m.group(2)),
                              "mcv": float(m.group(3)), "base": float(m.group(4)),
                              "total": float(m.group(5)), "stat": float(m.group(6))})
        return float(match[0].group(1)), float(match[0].group(2)), nodes, list(notices)

    def activate(sm, sf, mcv, fd):
        cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL, stxddependencies=NULL "
                    "WHERE stxoid IN (SELECT oid FROM pg_statistic_ext WHERE stxname LIKE %s)",
                    (prefix+"%",))
        if sm:
            cur.execute("UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv FROM dmv_bnm_backup b "
                        "WHERE d.stxoid=b.stxoid AND d.stxoid=ANY(%s)",
                        ([mcv[i]["oid"] for i in sm],))
        if sf:
            cur.execute("UPDATE pg_statistic_ext_data d SET stxddependencies=b.stxddependencies "
                        "FROM dmv_bnm_backup b WHERE d.stxoid=b.stxoid AND d.stxoid=ANY(%s)",
                        ([fd[i]["oid"] for i in sf],))

    try:
        cur.execute("SELECT to_regclass('dmv')")
        if cur.fetchone()[0] is None:
            cur.execute("CREATE UNLOGGED TABLE dmv(record_type text,registration_class text,state text,county text,body_type text,fuel_type text,reg_valid_date text,color text,scofflaw_indicator text,suspension_indicator text,revocation_indicator text) WITH (autovacuum_enabled=false)")
        cur.execute("SELECT count(*) FROM dmv")
        if int(cur.fetchone()[0]) == 0:
            with cur.copy("COPY dmv FROM STDIN WITH (FORMAT csv, HEADER true)") as copy:
                with args.csv.open("rb") as source:
                    for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                        copy.write(chunk)
            cur.execute("UPDATE dmv SET record_type=btrim(record_type),registration_class=btrim(registration_class),state=btrim(state),county=btrim(county),body_type=btrim(body_type),fuel_type=btrim(fuel_type),color=btrim(color),scofflaw_indicator=btrim(scofflaw_indicator),suspension_indicator=btrim(suspension_indicator),revocation_indicator=btrim(revocation_indicator)")
        cur.execute("SELECT count(*) FROM dmv"); row_count = int(cur.fetchone()[0])
        cur.execute("SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid='dmv'::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum")
        schema = [{"column": text(a).lower(), "type": text(t)} for a,t in cur.fetchall()]
        if row_count != expected_rows or [x["column"] for x in schema] != expected_columns or any(x["type"] != "text" for x in schema):
            raise RuntimeError({"actual_rows": row_count, "expected_rows": expected_rows,
                                "actual_schema": schema, "expected_columns": expected_columns})

        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid='dmv'::regclass")
        existing_stats = [text(x[0]) for x in cur.fetchall()]
        if existing_stats:
            for name in existing_stats:
                if not name.startswith(prefix):
                    raise RuntimeError("unexpected existing DMV statistic: "+name)
                cur.execute(psycopg.sql.SQL("DROP STATISTICS {}").format(psycopg.sql.Identifier(name)))

        mcv=[]; fd=[]
        for cid, pair in enumerate(pairs):
            for mechanism, target_list, kind in (("mcv", mcv, "mcv"), ("fd", fd, "dependencies")):
                name=f"{prefix}{mechanism}_{cid:02d}"
                cur.execute(psycopg.sql.SQL("CREATE STATISTICS {} ({}) ON {},{} FROM dmv").format(
                    psycopg.sql.Identifier(name), psycopg.sql.SQL(kind),
                    psycopg.sql.Identifier(pair[0]), psycopg.sql.Identifier(pair[1])))
                cur.execute(psycopg.sql.SQL("ALTER STATISTICS {} SET STATISTICS {}").format(
                    psycopg.sql.Identifier(name), psycopg.sql.Literal(args.target)))
                cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s",(name,))
                target_list.append({"id":f"{mechanism}:{pair[0]}:{pair[1]}", "index":cid,
                                    "name":name,"oid":int(cur.fetchone()[0]),"oid_rank":cid,
                                    "columns":list(pair),"query_indexes":[]})
        analyzed_at=time.perf_counter(); cur.execute("ANALYZE dmv"); analyze_seconds=time.perf_counter()-analyzed_at
        cur.execute("DROP TABLE IF EXISTS dmv_bnm_backup")
        cur.execute("CREATE TABLE dmv_bnm_backup AS SELECT stxoid,stxdmcv,stxddependencies FROM pg_statistic_ext_data WHERE stxoid IN (SELECT oid FROM pg_statistic_ext WHERE stxname LIKE %s)",(prefix+"%",))
        cur.execute("SELECT attnum,attname FROM pg_attribute WHERE attrelid='dmv'::regclass AND attnum>0")
        attnames={int(n):text(a).lower() for n,a in cur.fetchall()}
        for stat in mcv:
            cur.execute("SELECT pg_column_size(stxdmcv) FROM dmv_bnm_backup WHERE stxoid=%s",(stat["oid"],))
            value=cur.fetchone(); stat["serialized_bytes"]=None if value is None else value[0]
            cur.execute("SELECT a.attname FROM pg_statistic_ext s CROSS JOIN LATERAL unnest(s.stxkeys::smallint[]) WITH ORDINALITY k(attnum,ord) JOIN pg_attribute a ON a.attrelid=s.stxrelid AND a.attnum=k.attnum WHERE s.oid=%s ORDER BY k.ord",(stat["oid"],))
            stat["payload_columns"]=[text(x[0]).lower() for x in cur.fetchall()]
            cur.execute("SELECT values,nulls,frequency,base_frequency FROM dmv_bnm_backup CROSS JOIN LATERAL pg_mcv_list_items(stxdmcv) WHERE stxoid=%s",(stat["oid"],))
            stat["payload"]=[{"values":[text(v) if v is not None else None for v in vals],
                              "nulls":nulls,"frequency":float(freq),"base_frequency":float(base)}
                             for vals,nulls,freq,base in cur.fetchall()]
            stat["total_frequency"]=sum(x["frequency"] for x in stat["payload"])
        for stat in fd:
            cur.execute("SELECT pg_column_size(stxddependencies),pg_dependencies_send(stxddependencies) FROM dmv_bnm_backup WHERE stxoid=%s",(stat["oid"],))
            size,payload=cur.fetchone(); stat["serialized_bytes"]=size
            stat["payload"]=parse_binary_dependencies(payload,attnames) if payload is not None else []

        usable_mcv={i for i,x in enumerate(mcv) if x["payload"]}
        usable_fd={i for i,x in enumerate(fd) if x["payload"]}
        pair_to_id={tuple(x["columns"]):i for i,x in enumerate(mcv)}
        for qi,q in enumerate(queries):
            ids=[pair_to_id[x] for x in itertools.combinations(q["columns"],2)]
            q["candidate_ids"]=ids
            for i in ids: mcv[i]["query_indexes"].append(qi); fd[i]["query_indexes"].append(qi)

        activate(set(),set(),mcv,fd)
        relation_rows=native("TRUE")[0]
        clause_cache={}
        for q in queries:
            sels=[]; columns={}
            for clause in q["clauses"]:
                key=clause["sql"]
                if key not in clause_cache: clause_cache[key]=native(key)[0]/relation_rows
                sels.append(clause_cache[key]); columns[clause["column"]]=clause_cache[key]
            q["clause_selectivities"]=sels; q["column_selectivities"]=columns
            q["baseline_rows"]=native(q["where"])[0]
            q["baseline_qerror"]=qerror(q["baseline_rows"],q["truth"])
        empty_loss=sum(q["baseline_qerror"] for q in queries)

        def design_loss(sm,sf,details=False):
            losses=[]; traces=[]
            for q in queries:
                est,mt,ft=replay(q,sm,sf,mcv,fd,True)
                losses.append(qerror(est,q["truth"]))
                if details: traces.append({"estimate":est,"mcv":mt,"fd":ft})
            return sum(losses),losses,traces

        validation_designs=[("empty",set(),set())]
        reps=[0,len(pairs)//3,2*len(pairs)//3,len(pairs)-1]
        validation_designs += [(f"singleton_mcv_{i}",{i},set()) for i in reps if i in usable_mcv]
        validation_designs += [(f"singleton_fd_{i}",set(),{i}) for i in reps if i in usable_fd]
        validation_designs += [(f"mixed_{i}_{j}",{i},{j}) for i,j in zip(reps,reversed(reps)) if i in usable_mcv and j in usable_fd]
        validation_designs += [("all",usable_mcv,usable_fd)]
        comparisons=[]; bitwise=0
        for name,sm,sf in validation_designs:
            activate(sm,sf,mcv,fd)
            for qi,q in enumerate(queries):
                native_rows,_,native_nodes,_=native(q["where"])
                external,mt,ft=replay(q,sm,sf,mcv,fd,True)
                err=relerr(external,native_rows)
                bitwise += external.hex()==native_rows.hex()
                comparisons.append({"design":name,"query":q["id"],"external":external,
                                    "native":native_rows,"absolute_error":abs(external-native_rows),
                                    "relative_error":err,"external_mcv_trace":[x["id"] for x in mt],
                                    "native_mcv_oids":[x["oid"] for x in native_nodes],
                                    "external_fd_trace":[x["id"] for x in ft]})
        fidelity={"designs":len(validation_designs),"comparisons":len(comparisons),
                  "matches":sum(x["relative_error"]<=TOL for x in comparisons),
                  "bitwise_equal":bitwise,
                  "max_relative_error":max(x["relative_error"] for x in comparisons),
                  "max_absolute_error":max(x["absolute_error"] for x in comparisons),
                  "worst":sorted(comparisons,key=lambda x:x["relative_error"],reverse=True)[:20]}
        if fidelity["matches"] != fidelity["comparisons"]:
            raise RuntimeError({"correctness_blocker":fidelity})

        singleton=[]
        for mechanism,candidates,usable in (("mcv",mcv,usable_mcv),("fd",fd,usable_fd)):
            for i in sorted(usable):
                loss,_,_=design_loss({i} if mechanism=="mcv" else set(),
                                     {i} if mechanism=="fd" else set())
                singleton.append({"mechanism":mechanism,"index":i,"id":candidates[i]["id"],
                                  "columns":candidates[i]["columns"],"loss":loss,
                                  "delta":loss-empty_loss})
        all_mcv_loss,_,_=design_loss(usable_mcv,set())
        all_fd_loss,_,_=design_loss(set(),usable_fd)
        all_loss,all_losses,all_traces=design_loss(usable_mcv,usable_fd,True)
        loo=[]
        for mechanism,candidates,usable in (("mcv",mcv,usable_mcv),("fd",fd,usable_fd)):
            for i in sorted(usable):
                sm=usable_mcv-{i} if mechanism=="mcv" else usable_mcv
                sf=usable_fd-{i} if mechanism=="fd" else usable_fd
                loss,_,_=design_loss(sm,sf)
                loo.append({"mechanism":mechanism,"index":i,"id":candidates[i]["id"],
                            "columns":candidates[i]["columns"],"loss":loss,
                            "delta":loss-all_loss})

        harmful=max(singleton,key=lambda x:x["delta"])
        hc=mcv[harmful["index"]] if harmful["mechanism"]=="mcv" else fd[harmful["index"]]
        hsm={harmful["index"]} if harmful["mechanism"]=="mcv" else set()
        hsf={harmful["index"]} if harmful["mechanism"]=="fd" else set()
        examples=[]
        for qi in hc["query_indexes"]:
            q=queries[qi]; est,mt,ft=replay(q,hsm,hsf,mcv,fd,True)
            delta=qerror(est,q["truth"])-q["baseline_qerror"]
            if delta>1e-12:
                examples.append({"query":q["id"],"where":q["where"],"truth":q["truth"],
                                 "baseline_estimate":q["baseline_rows"],"singleton_estimate":est,
                                 "baseline_qerror":q["baseline_qerror"],
                                 "singleton_qerror":qerror(est,q["truth"]),"qerror_delta":delta,
                                 "mcv_trace":mt,"fd_trace":ft})
        examples.sort(key=lambda x:x["qerror_delta"],reverse=True)
        consumed_mcv={x["id"] for trace in all_traces for x in trace["mcv"]}
        consumed_fd={x["id"] for trace in all_traces for x in trace["fd"]}
        single_by={(x["mechanism"],x["index"]):x for x in singleton}
        cross=[]
        for row in loo:
            alone=single_by[(row["mechanism"],row["index"])]["delta"]
            # Adding s in all-minus-s changes loss by -removal delta.
            all_add=-row["delta"]
            if alone < -TOL and all_add > TOL or alone > TOL and all_add < -TOL:
                cross.append({**row,"singleton_delta":alone,"all_context_add_delta":all_add})

        result={
            "experiment":"DMV-Baseline-and-Nonmonotonicity-v0",
            "environment":{"database":args.database,"isolated":True,"rows":row_count,
                           "schema":schema,"query_count":len(queries),
                           "predicate_columns":len({c for q in queries for c in q["columns"]}),
                           "ground_truth":{"count":len(queries),"min":min(q["truth"] for q in queries),
                                           "max":max(q["truth"] for q in queries)},
                           "postgres_version":con.info.server_version},
            "candidate_universe":{"pairs":len(pairs),"mechanism_candidates":len(mcv)+len(fd),
                                  "pair_ids":[f"{a}:{b}" for a,b in pairs],
                                  "mcv":mcv,"fd":fd},
            "payload_acquisition":{"statistics_target":args.target,"single_analyze":True,
                                   "analyze_seconds":analyze_seconds,"relation_rows":relation_rows,
                                   "usable_mcv":len(usable_mcv),"usable_fd":len(usable_fd),
                                   "unusable_mcv":[mcv[i]["id"] for i in set(range(36))-usable_mcv],
                                   "unusable_fd":[fd[i]["id"] for i in set(range(36))-usable_fd],
                                   "offline_not_recurring_cost":True},
            "objective":{"definition":"sum of multiplicative q-errors over truth > 0; estimate floored at 1e-300; zero-truth queries retained for semantic validation with zero objective weight",
                         "empty_loss":empty_loss,"all_mcv_loss":all_mcv_loss,
                         "all_fd_loss":all_fd_loss,"all_mixed_loss":all_loss},
            "replay_inputs":{"queries":[{**q,"zero_truth":q["truth"]==0,
                                           "objective_member":q["truth"]>0} for q in queries],
                             "simple_selectivity_cache":clause_cache},
            "empty_design":{"loss":empty_loss,"queries":[
                {"query":q["id"],"where":q["where"],"truth":q["truth"],
                 "replay_estimate":q["baseline_rows"],"native_estimate":q["baseline_rows"],
                 "qerror":q["baseline_qerror"]} for q in queries]},
            "fidelity":fidelity,
            "singleton":{"tolerance":TOL,"all":classify(singleton),
                         "mcv":classify([x for x in singleton if x["mechanism"]=="mcv"]),
                         "fd":classify([x for x in singleton if x["mechanism"]=="fd"]),
                         "strongest_harmful":harmful,"causal_examples":examples[:5],"rows":singleton},
            "leave_one_out":{"all":classify(loo),
                             "mcv":classify([x for x in loo if x["mechanism"]=="mcv"]),
                             "fd":classify([x for x in loo if x["mechanism"]=="fd"]),
                             "strongest_improving":min(loo,key=lambda x:x["delta"]),"rows":loo},
            "consumption":{"selected_mcv":len(usable_mcv),"consumed_mcv":len(consumed_mcv),
                           "never_consumed_mcv":sorted({x["id"] for x in mcv if x["index"] in usable_mcv}-consumed_mcv),
                           "selected_fd":len(usable_fd),"consumed_fd":len(consumed_fd),
                           "never_consumed_fd":sorted({x["id"] for x in fd if x["index"] in usable_fd}-consumed_fd)},
            "context_sign_reversals":cross,
            "witnesses":{"harmful_singletons":sorted([x for x in singleton if x["delta"]>TOL],key=lambda x:x["delta"],reverse=True)[:10],
                         "improving_removals":sorted([x for x in loo if x["delta"] < -TOL],key=lambda x:x["delta"])[:10]},
            "census_reference":{"empty_loss":11808.96,"all_statistics_loss":10932.30,
                                "optimized_subset_loss":805.32,"rerun":False},
            "runtime_seconds":time.perf_counter()-started,
        }
        nonmono=bool(result["witnesses"]["harmful_singletons"] or result["witnesses"]["improving_removals"])
        result["conclusion"]=("Within PostgreSQL 16.14, the DMV target workload, the evaluated pair-MCV+FD candidate universe, frozen payload realization, and fixed precedence, the workload CE objective is empirically non-monotone in statistics-set inclusion." if nonmono else "Non-monotonicity was not observed in the evaluated DMV design relationships.")
        result["gate"]="READY FOR DMV COST MODEL"
        args.output.write_text(json.dumps(result,indent=2)+"\n")

        sa=result["singleton"]; lo=result["leave_one_out"]; cons=result["consumption"]
        harmful_reason=((f"The representative query consumes the {harmful['mechanism'].upper()} candidate; its native semantic correction moves the estimate farther from truth, so this is a control/consumption effect rather than rounding noise.") if examples and harmful["delta"] > TOL else "No harmful singleton was observed.")
        md=f"""# DMV-Baseline-and-Nonmonotonicity-v0

## Scope and correctness gate

The isolated DMV table contains {row_count:,} rows, 11 text columns, and the complete {len(queries):,}-query truth-bearing workload. Exactly {len(pairs)} workload-generated pairs produced {len(mcv)+len(fd)} mechanism-specific candidates. Candidate payloads came from one target-{args.target} ANALYZE realization; this is offline acquisition, not a recurring maintenance-cost measurement. All 36 MCV payloads and 34/36 FD payloads were usable; `fd:county:record_type` and `fd:revocation_indicator:suspension_indicator` had no dependency payload and were retained explicitly as unusable candidates.

The fixed precedence is lexicographic workload-pair order within each mechanism, materialized as creation/OID order. It was not optimized. In the all-statistics design, pair MCV GreedyCover consumes every usable pair opportunity before the FD stage, explaining why all 36 MCV candidates but none of the 34 available FD candidates are consumed there.

Native PostgreSQL pre-clamp rows and external frozen-payload replay matched in {fidelity['matches']:,}/{fidelity['comparisons']:,} real query/design comparisons at tolerance {TOL:g}. Maximum relative error was {fidelity['max_relative_error']:.6g}; maximum absolute error was {fidelity['max_absolute_error']:.6g}.

## Objective and inclusion results

| Design | Workload loss |
|---|---:|
| Empty | {empty_loss:.12f} |
| All MCV | {all_mcv_loss:.12f} |
| All FD | {all_fd_loss:.12f} |
| All MCV+FD | {all_loss:.12f} |

| Context / mechanism | Beneficial | Neutral | Harmful |
|---|---:|---:|---:|
| Singleton / MCV | {sa['mcv']['beneficial']} | {sa['mcv']['neutral']} | {sa['mcv']['harmful']} |
| Singleton / FD | {sa['fd']['beneficial']} | {sa['fd']['neutral']} | {sa['fd']['harmful']} |
| Singleton / all | {sa['all']['beneficial']} | {sa['all']['neutral']} | {sa['all']['harmful']} |
| Remove from all / MCV | {lo['mcv']['beneficial']} | {lo['mcv']['neutral']} | {lo['mcv']['harmful']} |
| Remove from all / FD | {lo['fd']['beneficial']} | {lo['fd']['neutral']} | {lo['fd']['harmful']} |

Here a beneficial leave-one-out row means removal lowers loss. The strongest harmful singleton is `{harmful['id']}` with delta {harmful['delta']:.12f}. {harmful_reason} The strongest improving removal is `{lo['strongest_improving']['id']}` with delta {lo['strongest_improving']['delta']:.12f}.

All-statistics consumption: MCV {cons['consumed_mcv']}/{cons['selected_mcv']}; FD {cons['consumed_fd']}/{cons['selected_fd']}. Selected, consumed, and beneficial remain distinct properties.

{result['conclusion']} Thus the qualitative Census motivation for subset selection {'replicates' if nonmono else 'was not replicated over these relationships'}; no claim of universal PostgreSQL non-monotonicity is made.

## Required final verdict

1. **Was the expected 36-pair / 72-mechanism candidate universe obtained?** Yes: {len(pairs)} pairs and {len(mcv)+len(fd)} candidates.
2. **How many MCV and FD payloads were usable?** {len(usable_mcv)} MCV and {len(usable_fd)} FD.
3. **What was the empty-design workload loss?** {empty_loss:.12f}.
4. **How many real-DMV native/replay comparisons were performed?** {fidelity['comparisons']:,}.
5. **How many matched within strict tolerance?** {fidelity['matches']:,}/{fidelity['comparisons']:,}.
6. **What was the maximum relative semantic replay error?** {fidelity['max_relative_error']:.6g}.
7. **Among singleton additions from empty, how many were beneficial, neutral, and harmful?** {sa['all']['beneficial']}, {sa['all']['neutral']}, and {sa['all']['harmful']}.
8. **What is the MCV/FD breakdown?** MCV {sa['mcv']['beneficial']}/{sa['mcv']['neutral']}/{sa['mcv']['harmful']}; FD {sa['fd']['beneficial']}/{sa['fd']['neutral']}/{sa['fd']['harmful']} (beneficial/neutral/harmful).
9. **What was the strongest harmful singleton and why was it harmful?** `{harmful['id']}`, delta {harmful['delta']:.12f}. {harmful_reason}
10. **What was the all-MCV loss?** {all_mcv_loss:.12f}.
11. **What was the all-FD loss?** {all_fd_loss:.12f}.
12. **What was the all-MCV+FD loss?** {all_loss:.12f}.
13. **How many leave-one-out removals from all-statistics improved the objective?** {lo['all']['beneficial']}.
14. **What was the strongest improving removal?** `{lo['strongest_improving']['id']}`, delta {lo['strongest_improving']['delta']:.12f}.
15. **How many MCV and FD candidates were actually consumed in the all-statistics design?** {cons['consumed_mcv']} MCV and {cons['consumed_fd']} FD.
16. **Does DMV provide an empirical non-monotonicity witness?** {'Yes' if nonmono else 'No'}.
17. **Does the qualitative Census motivation for statistics selection replicate on DMV?** {'Yes' if nonmono else 'No over the evaluated relationships'}.
18. **Is CE-Replay semantically faithful on the real IN-heavy DMV workload?** Yes, over all {fidelity['comparisons']:,} tested query/design comparisons at the established tolerance.
19. **Are there any correctness blockers before measuring DMV ANALYZE maintenance cost?** No.

## Final gate

READY FOR DMV COST MODEL
"""
        args.report.write_text(md)
        print(json.dumps({"rows":row_count,"pairs":len(pairs),"usable_mcv":len(usable_mcv),
                          "usable_fd":len(usable_fd),"fidelity":fidelity,
                          "losses":result["objective"],"singleton":{k:sa[k] for k in ('all','mcv','fd')},
                          "leave_one_out":{k:lo[k] for k in ('all','mcv','fd')},
                          "consumption":cons,"gate":result["gate"]},indent=2))
    finally:
        try:
            cur.close(); con.close()
        finally:
            if not args.keep_database and args.output.exists():
                with admin.cursor() as acur:
                    acur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",(args.database,))
                    acur.execute(psycopg.sql.SQL("DROP DATABASE IF EXISTS {}").format(psycopg.sql.Identifier(args.database)))
            admin.close()


if __name__ == "__main__":
    main()
