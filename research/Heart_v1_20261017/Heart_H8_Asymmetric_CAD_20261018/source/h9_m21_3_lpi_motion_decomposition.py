#!/usr/bin/env python3
"""W3 M21.3: read-only exact LPI line-plane motion decomposition.

Uses six SHA-bound M18/M19 packets and M21.1 source-motion attachments.
No Cherchi Boolean, no native source call, no build, no Newton admission.
"""
from __future__ import annotations
import argparse, json, math, sys, traceback
from fractions import Fraction as F
from pathlib import Path
import h9_m21_motion_math as mm

FEATURES = {
    "repeated": ((3756, 3813), (24, 86, 87)),
    "left-full": ((9992, 10119), (31, 105, 110)),
    "right-first": ((3168, 3618), (24, 151, 152)),
}
SEQUENCES = {"left": (0, 4, 1), "right": (2, 5, 3)}
INTERVALS = (("full", 0, 2), ("first-half", 0, 1), ("second-half", 1, 2))


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def norm(v):
    return math.sqrt(float(sum((x*x for x in v), F(0))))


def fstr(x):
    return f"{x.numerator}/{x.denominator}"


def feature_key(line, plane):
    return ("LPI", tuple(sorted((0, int(i)) for i in line)),
            tuple(sorted((1, int(i)) for i in plane)))


def operand_velocity(operand, source_velocity):
    choices = operand.get("source_vertices")
    need(operand.get("status") == "UNIQUE" and type(choices) is list and len(choices) == 1,
         "LPI_OPERAND_NOT_UNIQUE")
    ref = choices[0]
    obj, index = ref.get("input_object"), ref.get("input_vertex")
    need(type(obj) is int and obj in (0, 1), "LPI_BAD_INPUT_OBJECT")
    need(type(index) is int and index >= 0, "LPI_BAD_INPUT_VERTEX")
    if obj == 0:
        return mm.ZERO
    need(index < len(source_velocity), "LPI_SOURCE_VELOCITY_INDEX_OOB")
    return mm.vec(source_velocity[index])


def decompose_lpi(raw_record, resolved_record, source_velocity):
    """Exact quotient-rule decomposition in the physical input frame."""
    need(raw_record.get("point_type") == "LPI" and
         resolved_record.get("point_type") == "LPI", "NOT_LPI_RECORD")
    raw = raw_record.get("operand_coordinates_exact")
    ops = resolved_record.get("operands")
    need(type(raw) is list and len(raw) == 5 and type(ops) is list and len(ops) == 5,
         "LPI_OPERAND_COUNT")
    p = [mm.vec(x) for x in raw]
    v = [operand_velocity(o, source_velocity) for o in ops]
    A, B, P, Q, R = p
    vA, vB, vP, vQ, vR = v
    u, du = mm.sub(B, A), mm.sub(vB, vA)
    w, dw = mm.sub(P, A), mm.sub(vP, vA)
    q, r = mm.sub(Q, P), mm.sub(R, P)
    n = mm.cross(q, r)
    dn = mm.add(mm.cross(mm.sub(vQ, vP), r),
                mm.cross(q, mm.sub(vR, vP)))
    d = mm.dot(n, u)
    need(d != 0, "LPI_EXACT_PARALLEL_OR_DEGENERATE")
    d_plane, d_line = mm.dot(dn, u), mm.dot(n, du)
    dprime = d_plane + d_line
    numerator = mm.dot(n, w)
    num_plane, num_point = mm.dot(dn, w), mm.dot(n, dw)
    numprime = num_plane + num_point
    t = numerator / d
    t_plane = (num_plane*d - numerator*d_plane) / (d*d)
    t_point = num_point / d
    t_line = -numerator*d_line / (d*d)
    tprime = t_plane + t_point + t_line
    position = mm.add(A, mm.mul(t, u))
    velocity = mm.add(vA, mm.add(mm.mul(tprime, u), mm.mul(t, du)))
    n_norm, u_norm = norm(n), norm(u)
    need(n_norm > 0 and u_norm > 0, "LPI_ZERO_NORMAL_OR_LINE")
    return {
        "line_input_ids": [[ops[i]["source_vertices"][0]["input_object"],
                            ops[i]["source_vertices"][0]["input_vertex"]] for i in (0, 1)],
        "plane_input_ids": [[ops[i]["source_vertices"][0]["input_object"],
                             ops[i]["source_vertices"][0]["input_vertex"]] for i in (2, 3, 4)],
        "d_exact": fstr(d), "abs_d": float(abs(d)),
        "dprime_plane": fstr(d_plane), "dprime_line": fstr(d_line),
        "dprime_total": fstr(dprime),
        "relative_denominator_rate_per_c7": float(abs(dprime/d)),
        "normal_norm": n_norm, "normal_derivative_norm": norm(dn),
        "relative_normal_rate_per_c7": norm(dn)/n_norm,
        "line_direction_norm": u_norm, "line_direction_derivative_norm": norm(du),
        "normalized_incidence": float(abs(d))/(n_norm*u_norm),
        "numerator_exact": fstr(numerator),
        "numerator_prime_plane": fstr(num_plane),
        "numerator_prime_point": fstr(num_point),
        "numerator_prime_total": fstr(numprime),
        "t_exact": fstr(t), "t": float(t),
        "tprime_plane_denominator": fstr(t_plane),
        "tprime_point_motion": fstr(t_point),
        "tprime_line_motion": fstr(t_line),
        "tprime_total": fstr(tprime), "abs_tprime": float(abs(tprime)),
        "position_exact": [fstr(x) for x in position],
        "velocity_exact": [fstr(x) for x in velocity],
        "intersection_velocity_norm": norm(velocity),
        "velocity_anchor_norm": norm(vA),
        "velocity_parameter_term_norm": norm(mm.mul(tprime, u)),
        "velocity_line_term_norm": norm(mm.mul(t, du)),
        "decomposition_identity_exact": (
            tprime == t_plane+t_point+t_line
            and velocity == mm.add(vA, mm.add(mm.mul(tprime, u), mm.mul(t, du)))
        ),
    }


def records_by_feature(material):
    raw = {r["vertex_index"]: r for r in material["material_proof"]["construction_records"]}
    resolved = {r["vertex_index"]: r for r in material["material_proof"]["resolved_construction_records"]}
    out = {}
    for i, rr in resolved.items():
        if rr.get("point_type") == "LPI":
            out[mm.key_for("LPI", rr["operands"])] = (raw[i], rr)
    return out


def run(args):
    import h9_m21_layered_replay as replay
    ledger = replay.load_ledger(args.precision_ledger)
    doc = replay.frozen_request(args.artifact)
    packets, plan, input_hashes = replay.load_six(args, ledger)
    src_report_path = args.m21_source_run / "layered-report.json"
    src_report = replay.read_json(src_report_path)
    need(src_report.get("schema") == "heart-h9-m21-layered-motion-diagnostic-v1"
         and src_report.get("status") == "SOURCE_MOTION_AND_EXACT_CHAIN_REPLAYED_DIAGNOSTIC_ONLY",
         "M21_SOURCE_REPORT_NOT_SUCCESSFUL")
    need(src_report.get("new_native_source_calls_this_run") == 6
         and src_report.get("new_boolean_calls_this_run") == 0
         and src_report.get("newton_admitted") is False, "M21_SOURCE_SCOPE_INVALID")
    worker_report = args.m21_source_run / "worker" / "layered-report.json"
    if src_report.get("worker_report_sha256"):
        replay.bind_file(worker_report, src_report["worker_report_sha256"])
    rows = {x["stem"]: x for x in src_report["packet_results"]}
    need(len(rows) == 6, "M21_SOURCE_PACKET_COUNT")
    attachments = []
    for mat, meta, ev in packets:
        stem = ev["stem"]
        row = rows.get(stem)
        need(row is not None, "M21_SOURCE_STEM_MISSING:"+stem)
        ap = args.m21_source_run / "worker" / (stem + ".source-motion.json")
        replay.bind_file(ap, row["source_motion_attachment_sha256"])
        att = replay.read_json(ap)
        need(att.get("schema") == "heart-h9-m21-source-only-motion-v1"
             and att.get("material_sha256") == ev["material_sha256"]
             and att.get("native_core_sha256") == src_report["native_core_sha256"]
             and att.get("boolean_calls") == 0 and att.get("newton_admitted") is False,
             "SOURCE_ATTACHMENT_BINDING_OR_SCOPE_MISMATCH")
        vel = att.get("physical_source_velocity_column7")
        need(type(vel) is list and len(vel) == len(mat["quadric_source_vertices"]),
             "SOURCE_VELOCITY_COUNT_MISMATCH")
        attachments.append((att, vel))

    keys = {name: feature_key(*spec) for name, spec in FEATURES.items()}
    packet_results, states = [], []
    for (mat, meta, ev), (att, vel) in zip(packets, attachments):
        state = mm.material_state(mat, doc["request"], vel)
        states.append(state)
        lpis = records_by_feature(mat)
        feature_rows = {}
        for name, key in keys.items():
            need(key in lpis, "TARGET_LPI_NOT_PRESENT:"+ev["stem"]+":"+name)
            raw, resolved = lpis[key]
            detail = decompose_lpi(raw, resolved, vel)
            pts = [mm.vec(x) for x in raw["operand_coordinates_exact"]]
            vels = [operand_velocity(o, vel) for o in resolved["operands"]]
            pos2, vel2 = mm.construction("LPI", pts, vels)
            need(pos2 == tuple(mm.frac(x) for x in detail["position_exact"]),
                 "LPI_POSITION_DECOMPOSITION_MISMATCH")
            need(vel2 == tuple(mm.frac(x) for x in detail["velocity_exact"]),
                 "LPI_VELOCITY_DECOMPOSITION_MISMATCH")
            pos_target = mm.to_target(pos2, doc["request"])
            vel_target = mm.to_target(vel2, doc["request"], True)
            need(pos_target == state["positions"][key],
                 "LPI_TARGET_POSITION_BINDING_MISMATCH")
            need(vel_target == state["motion"][key],
                 "LPI_TARGET_VELOCITY_BINDING_MISMATCH")
            detail["m21_target_frame_position_and_velocity_bound"] = True
            feature_rows[name] = detail
        packet_results.append({
            "stem": ev["stem"], "material_sha256": ev["material_sha256"],
            "features": feature_rows, "boolean_calls": 0,
            "native_source_calls_this_run": 0, "newton_admitted": False,
        })

    pair_results = []
    for side, seq in SEQUENCES.items():
        for interval, a, b in INTERVALS:
            i, j = seq[a], seq[b]
            delta = F(states[j]["c7"]) - F(states[i]["c7"])
            need(delta > 0, "BAD_C7_INTERVAL")
            feature_rows = {}
            for name, key in keys.items():
                secant = mm.mul(1/delta, mm.sub(states[j]["positions"][key], states[i]["positions"][key]))
                average = mm.mul(F(1,2), mm.add(states[i]["motion"][key], states[j]["motion"][key]))
                residual = mm.sub(secant, average)
                feature_rows[name] = {
                    "delta_c7": float(delta),
                    "position_secant": [float(x) for x in secant],
                    "endpoint_average_velocity": [float(x) for x in average],
                    "signed_residual": [float(x) for x in residual],
                    "max_abs_residual": float(max(abs(x) for x in residual)),
                    "residual_norm": norm(residual),
                    "average_velocity_norm": norm(average),
                    "relative_residual_if_nonzero": norm(residual)/norm(average) if norm(average) else None,
                }
            pair_results.append({
                "side": side, "interval": interval,
                "from_stem": packets[i][2]["stem"], "to_stem": packets[j][2]["stem"],
                "features": feature_rows,
            })
    for path, sha in input_hashes.items():
        replay.bind_file(path, sha)
    replay.bind_file(args.precision_ledger, replay.LEDGER_SHA)
    return {
        "schema": "heart-h9-m21-3-lpi-motion-decomposition-v1",
        "status": "SIX_PACKET_LPI_MOTION_DECOMPOSITION_COMPLETE_DIAGNOSTIC_ONLY",
        "analysis_scope": "SAVED_SIX_PACKETS_AND_REPLAYED_BINARY64_SOURCE_VELOCITIES",
        "source_report_sha256": replay.file_hash(src_report_path),
        "precision_ledger_sha256": replay.LEDGER_SHA,
        "packet_results": packet_results,
        "same_side_interval_lpi_secants": pair_results,
        "new_boolean_calls_this_run": 0, "new_native_source_calls_this_run": 0,
        "root_cause_determined": False, "continuous_neighborhood_certified": False,
        "newton_admitted": False, "final_heart_obj_produced": False,
        "next_gate": "INTERPRET_LPI_DENOMINATOR_AND_MOTION_TERMS_NOT_NEWTON",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for flag in ("precision-ledger", "artifact", "stage17-native-dir", "m19-run", "m21-source-run", "output"):
        ap.add_argument("--"+flag, required=True, type=Path)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    args = ap.parse_args(argv)
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        result = run(args)
        with (args.output/"lpi-decomposition.json").open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, sort_keys=True, allow_nan=False); f.write("\n")
        print("M21_3_STATUS", result["status"])
        print("M21_3_PACKETS", len(result["packet_results"]))
        print("M21_3_BOOLEAN_CALLS", 0)
        print("M21_3_SOURCE_CALLS", 0)
        print("M21_3_NEWTON", False)
        return 0
    except Exception as exc:
        failure = {"schema":"heart-h9-m21-3-failure-v1",
                   "status":"FAILED_CLOSED_DIAGNOSTIC_ONLY",
                   "reason":f"{type(exc).__name__}: {exc}",
                   "traceback":traceback.format_exc(),
                   "new_boolean_calls_this_run":0,
                   "new_native_source_calls_this_run":0,"newton_admitted":False}
        with (args.output/"failure.json").open("x", encoding="utf-8") as f:
            json.dump(failure, f, indent=2, sort_keys=True); f.write("\n")
        print(failure["reason"])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
