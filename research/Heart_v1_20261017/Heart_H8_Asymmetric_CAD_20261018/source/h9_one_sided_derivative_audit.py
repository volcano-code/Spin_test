"""Independent H9 finite one-sided moment/Jacobian diagnostics for FOUR real side packets.

Consumes ONLY material-derived ten moments and same-call Jacobian columns after
external packet integrity checks; never derives a continuous smooth stratum or
allows Newton. Pure math here can be unit-tested with explicitly synthetic data.
"""
from __future__ import annotations

import math

EXPECTED = ((0, 'left-coarse'), (1, 'left-near'), (2, 'right-near'), (3, 'right-coarse'))


def require(test, reason):
    if not test:
        raise ValueError(reason)


def finite_ten(values, reason):
    require(isinstance(values, list) and len(values)==10 and
            all(type(x) in (float, int) and math.isfinite(x) for x in values), reason)
    return values


def one_sided_diagnostics(samples, *, same_symbolic_left, same_symbolic_right):
    """Compare independent secants to both same-side production Jacobian columns.

    The 0,1 and 2,3 comparisons never cross the candidate event root.
    Boolean side flags are exact finite combinatorics, NOT continuous proof.
    """
    require(isinstance(samples, list) and len(samples)==4, 'FOUR_FRESH_NATIVE_SIDE_ROWS_REQUIRED')
    require([(x.get('index'), x.get('side')) for x in samples] == list(EXPECTED),
            'UNEXPECTED_EVENT_SIDE_ORDER')
    require(type(same_symbolic_left) is bool and type(same_symbolic_right) is bool,
            'MISSING_EXACT_FINITE_PAIR_SEMANTICS')
    for item in samples:
        require(type(item.get('c7')) in (int,float) and math.isfinite(item['c7']),
                'NONFINITE_OR_MISSING_NATIVE_C7')
        finite_ten(item.get('recomputed_exact_moments'), 'MISSING_REINTEGRATED_TEN_MOMENTS')
        finite_ten(item.get('native_recorded_jacobian_col7'), 'MISSING_SAME_CALL_JACOBIAN_COLUMN7')
    t=[item['c7'] for item in samples]
    require(all(t[i] < t[i+1] for i in range(3)), 'NATIVE_SIDE_POINTS_NOT_STRICTLY_ORDERED')
    output=[]
    for i,j,side,same in ((0,1,'left',same_symbolic_left),(2,3,'right',same_symbolic_right)):
        delta=t[j]-t[i]
        a,b=samples[i],samples[j]
        secant=[(b['recomputed_exact_moments'][k]-a['recomputed_exact_moments'][k])/delta
                for k in range(10)]
        require(all(math.isfinite(x) for x in secant), 'NONFINITE_FINITE_DIFFERENCE_SLOPE')
        jaca=a['native_recorded_jacobian_col7']
        jacb=b['native_recorded_jacobian_col7']
        e0=max(abs(secant[k]-jaca[k])/max(1.,abs(jaca[k])) for k in range(10))
        e1=max(abs(secant[k]-jacb[k])/max(1.,abs(jacb[k])) for k in range(10))
        output.append({'side':side,'indices':[i,j],'delta_c7':delta,
                       'independently_reintegrated_ten_moment_secant':secant,
                       'max_scaled_difference_vs_first_native_jacobian':e0,
                       'max_scaled_difference_vs_second_native_jacobian':e1,
                       'finite_pair_exact_symbolic_patch_identity_same':same,
                       'qualified_continuous_smooth_branch':False,
                       'qualified_Newton_derivative':False})
    return {'schema':'heart-h9-two-sided-finite-jacobian-diagnostics-v1',
            'finite_same_side_pairs':output,'both_finite_pairs_same_symbolic_support':
                same_symbolic_left and same_symbolic_right,
            'cross_event_secant_is_smooth_derivative':False,
            'continuous_neighborhood_certified':False,
            'newton_admitted':False}
