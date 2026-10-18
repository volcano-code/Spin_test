"""H9 finite-sample *exact* edge-event witness from frozen Actions artifact.

No Boolean is run here. Sign change of the four-point determinant indicates a
candidate edge-edge event; an actual continuous branch interval / Newton
admission is NOT established. All input material gzips are SHA-verified.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import gzip
import json
from pathlib import Path
import zipfile

from audit_h9_branch_decision import (
    ZIP_SHA256, REQUEST_SHA256, REPORT_PREFIX, REQUEST_PATH,
    CLASSIFICATION_PATH, REPORT_PATH, det4, digest, exact_point,
    file_digest, fraction_witness, require, sign,
)

SAMPLES = (0, 57, 58, 59, 60, 61, 62, 63, 64)
SOURCE_EDGE = (24, 90)
DESIGN_EDGE = (5517, 5518)
SOURCE_NEIGHBORS = ((24, 89, 90), (24, 90, 151))
DESIGN_NEIGHBORS = ((5516, 5517, 5518), (5517, 5518, 5523))
# Interior candidates deliberately avoid pretending to be a certified root.
PROBE_DELTAS = ('0.000001875', '0.00000225', '0.000002625')


def adjacent_face_ids(faces, edge):
    return [(i, tuple(sorted(face))) for i, face in enumerate(faces)
            if set(edge).issubset(face)]


def exact_secant(d0: Fraction, d1: Fraction, v0: Fraction, v1: Fraction):
    require(d0 < d1 and v0 > 0 and v1 < 0, 'NO_OBSERVED_SIGN_BRACKET')
    candidate = d0 + (d1 - d0) * v0 / (v0 - v1)
    require(d0 < candidate < d1, 'SECANT_OUTSIDE_FINITE_SAMPLE_ENDPOINTS')
    return candidate


def locate(artifact: Path) -> dict:
    require(file_digest(artifact) == ZIP_SHA256, 'NOT_FROZEN_ACTIONS_ARTIFACT_ZIP_SHA256')
    with zipfile.ZipFile(artifact) as z:
        req_bytes = z.read(REQUEST_PATH)
        require(digest(req_bytes) == REQUEST_SHA256, 'FROZEN_REQUEST_SHA_DRIFT')
        frozen = json.loads(req_bytes)
        report_bytes = z.read(REPORT_PATH)
        report = json.loads(report_bytes)
        classification = json.loads(z.read(CLASSIFICATION_PATH))
        require(frozen['schema'] == 'spin-heart-h8-faster-preparation-v1'
                and frozen['evidence']['scope'] == 'H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED'
                and report['input_request_sha256'] == REQUEST_SHA256
                and report['completed_samples'] == 81
                and report['all_numerical_checks_passed'] is True
                and report['qualified_branch_neighborhood'] is False
                and report['formal_newton_converged'] is False
                and classification['source_report_sha256'] == digest(report_bytes)
                and classification['complete_material_snapshots_verified'] == 81
                and classification['classifications'] == {
                    'CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE': 1,
                    'SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED': 79,
                }, 'NOT_FROZEN_FAILED_H8F_CONSTRUCTION_PROTOCOL')
        statuses = {row['index']: row['status'] for row in classification['comparisons']}
        require(set(statuses) == set(range(1, 81)) and
                [i for i, s in statuses.items() if s !=
                 'SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'] == [60],
                'NOT_SINGLE_SAMPLE_60_SEMANTIC_EXCEPTION')
        design_vertices = frozen['request']['design_vertices']
        design = [exact_point(design_vertices[i]) for i in DESIGN_EDGE]
        d_adj = adjacent_face_ids(frozen['request']['design_faces'], DESIGN_EDGE)
        require(len(d_adj) == 2 and {v for _, v in d_adj} == set(DESIGN_NEIGHBORS),
                'DESIGN_EDGE_NOT_TWO_EXPECTED_EXACT_FACETS')
        base = report['target_q']
        entries = []
        exact_values = {}
        for i in SAMPLES:
            prefix = REPORT_PREFIX + f'point-{i:03d}'
            sample = json.loads(z.read(prefix + '.json'))
            data = z.read(prefix + '-material.json.gz')
            require(digest(data) == sample['exact_same_call_material_archive_sha256'],
                    f'UNVERIFIED_POINT_MATERIAL_{i}')
            material = json.loads(gzip.decompress(data))
            require(sample['index'] == i and sample['coefficients'] == material['quadric_coefficients']
                    and sample['feature_branch_hash'] == material['topology_hash']
                    and sample['material_geometry_hash'] == material['geometry_hash']
                    and sample['exact_native_material_boundary_passed'] is True
                    and material['material_proof']['schema'] == 'cherchi-same-call-material-v1'
                    and len(material['quadric_source_vertices']) == 162
                    and len(material['quadric_source_faces']) == 320
                    and len(sample['independent_variable_raw_moments']) == 10,
                    f'INVALID_REAL_SAMPLE_{i}')
            c = sample['coefficients']
            require(all(c[j] == base[j] for j in range(10) if j != 7),
                    f'OTHER_COEFFICIENT_DRIFT_{i}')
            s_adj = adjacent_face_ids(material['quadric_source_faces'], SOURCE_EDGE)
            require(len(s_adj) == 2 and {v for _, v in s_adj} == set(SOURCE_NEIGHBORS),
                    f'SOURCE_EDGE_NOT_TWO_EXPECTED_FACETS_{i}')
            source = [exact_point(material['quadric_source_vertices'][j]) for j in SOURCE_EDGE]
            determinant = det4(source[0], source[1], design[0], design[1])
            require(determinant != 0, f'SAMPLED_EXACT_ZERO_EVENT_{i}')
            exact_values[i] = determinant
            entries.append({
                'index': i, 'coefficient_7': c[7],
                'perturbation_delta_str': str(c[7] - base[7]),
                'det_source24_90_design5517_5518': fraction_witness(determinant),
                'construction_classification': 'BASELINE' if i == 0 else statuses[i],
                'material_zip_member_sha256': digest(data),
                'independent_ten_moments': sample['independent_variable_raw_moments'],
                'source_edge_face_ids': [idx for idx, _ in s_adj],
            })
        expected_signs = {0:1, 57:1, 58:1, 59:1, 60:-1, 61:1, 62:1, 63:1, 64:1}
        require({i: sign(v) for i,v in exact_values.items()} == expected_signs,
                'REAL_POINT_EDGE_DETERMINANT_SIGN_DRIFT')
        c59 = next(x for x in entries if x['index'] == 59)
        c60 = next(x for x in entries if x['index'] == 60)
        lower = Fraction(str(c59['coefficient_7']))
        upper = Fraction(str(c60['coefficient_7']))
        predicted = exact_secant(lower, upper, exact_values[59], exact_values[60])
        jac7 = [row[7] for row in report['analytic_10_by_10_jacobian']]
        # These are ACTUAL archived independent material moment values; a
        # small secant discrepancy is not evidence of a single smooth branch.
        h = c60['coefficient_7'] - c59['coefficient_7']
        slopes = [(y-x)/h for x,y in zip(c59['independent_ten_moments'],
                                        c60['independent_ten_moments'])]
        maxerr = max(abs(a-b)/max(1.0,abs(b)) for a,b in zip(slopes,jac7))
        return {
            'schema':'heart-h9-exact-edge-event-sample-bracket-v1',
            'frozen_run_id':39123384402, 'frozen_run_conclusion':'failure',
            'artifact_id':12135528290, 'artifact_zip_sha256':ZIP_SHA256,
            'request_sha256':REQUEST_SHA256,
            'source_81_point_report_sha256':digest(report_bytes),
            'source_81_point_classification_sha256':digest(z.read(CLASSIFICATION_PATH)),
            'source_edge':list(SOURCE_EDGE), 'design_edge':list(DESIGN_EDGE),
            'source_adjacent_facets':[list(x) for x in SOURCE_NEIGHBORS],
            'design_adjacent_facets':[list(x) for x in DESIGN_NEIGHBORS],
            'edge_event_invariant':'det(source[24],source[90],design[5517],design[5518])',
            'real_archived_samples':entries,
            'measured_opposite_sign_endpoints':{'lower_index':59,'upper_index':60,
                   'lower_c7':float(lower),'upper_c7':float(upper),
                   'lower_sign':1,'upper_sign':-1},
            'secant_predicted_c7_not_certified_event':float(predicted),
            'secant_within_measured_interval':True,
            'live_probe_candidate_c7':[float(Fraction(x)) for x in PROBE_DELTAS] + [float(predicted)],
            'archived_finite_secant_59_to_60':{'ten_moment_slopes':slopes,
                'base_analytic_column7':jac7, 'max_scaled_deviation_from_base_jacobian':maxerr},
            'new_native_calls_this_run':0, 'actual_continuous_event_localized':False,
            'real_geometry_boundary_discontinuity_proven':False,
            'continuous_smooth_neighborhood_proven':False, 'newton_admitted':False,
            'final_heart_obj_produced':False,
        }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=locate(a.artifact)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False)
        f.write('\n')
    print('H9_REAL_ARCHIVED_EXACT_DETERMINANT_SIGNS', [(x['index'],x['det_source24_90_design5517_5518']['sign']) for x in result['real_archived_samples']])
    print('H9_SECANT_C7_PREDICTION_NOT_CERTIFIED',result['secant_predicted_c7_not_certified_event'])
    print('H9_NEWTON_DENIED_NO_NEW_NATIVE_EVALUATIONS')

if __name__=='__main__':
    main()
