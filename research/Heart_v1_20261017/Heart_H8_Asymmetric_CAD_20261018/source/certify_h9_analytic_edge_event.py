"""H9 offline proof for a *surrogate* fixed-normal inverse-Gauss edge event.

Actual input: SHA-verified H8f native Cherchi snapshots. All interval results
use integer fixed-point outward rounding: no float is used to decide signs.
This does NOT run a fresh Cherchi Boolean, certify the production continuous
branch, or authorize Newton.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction as F
import gzip
from hashlib import sha256
from math import isqrt
import json
from pathlib import Path
import zipfile

ARTIFACT_SHA = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
REQUEST_SHA = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
SCALE = 10**38
INDICES = (0, 57, 58, 59, 60, 61, 62, 63, 64)
SOURCE_IDS = (24, 89, 90, 151)
DESIGN_IDS = (5517, 5518)
LOW = F('0.0000015')
HIGH = F('0.000003')


def require(ok, code):
    if not ok:
        raise ValueError(code)


def frac(number):
    if isinstance(number, F):
        return number
    if isinstance(number, float):
        return F.from_float(number)
    return F(number)


def upper_div(a, b):
    return -((-a)//b)


@dataclass(frozen=True)
class Interval:
    lo: int
    hi: int

    def __post_init__(self):
        require(self.lo <= self.hi, 'EMPTY_RATIONAL_INTERVAL')

    @staticmethod
    def const(number):
        value = frac(number)
        n = value.numerator * SCALE
        d = value.denominator
        return Interval(n//d, upper_div(n, d))

    @staticmethod
    def between(lo, hi):
        return Interval(Interval.const(lo).lo, Interval.const(hi).hi)

    def __add__(self, other):
        other = as_interval(other)
        return Interval(self.lo + other.lo, self.hi + other.hi)

    __radd__ = __add__

    def __neg__(self):
        return Interval(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + (-as_interval(other))

    def __rsub__(self, other):
        return as_interval(other) - self

    def __mul__(self, other):
        other = as_interval(other)
        options = [a*b for a in (self.lo, self.hi) for b in (other.lo, other.hi)]
        return Interval(min(options)//SCALE, upper_div(max(options), SCALE))

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = as_interval(other)
        require(other.lo > 0 or other.hi < 0, 'INTERVAL_DIVISION_BY_ZERO')
        candidates = [(a*SCALE, b) for a in (self.lo, self.hi)
                      for b in (other.lo, other.hi)]
        return Interval(min(a//b for a,b in candidates),
                        max(upper_div(a,b) for a,b in candidates))

    def __rtruediv__(self, other):
        return as_interval(other) / self

    def sqrt(self):
        require(self.lo >= 0, 'NEGATIVE_SQUARE_ROOT_INTERVAL')
        lower = isqrt(self.lo*SCALE)
        upper = isqrt(self.hi*SCALE)
        if upper*upper != self.hi*SCALE:
            upper += 1
        return Interval(lower, upper)

    def sign(self):
        if self.lo > 0:
            return 1
        if self.hi < 0:
            return -1
        if self.lo == 0 and self.hi == 0:
            return 0
        return None

    def as_floats(self):
        return [float(F(self.lo, SCALE)), float(F(self.hi, SCALE))]


def as_interval(value):
    return value if isinstance(value, Interval) else Interval.const(value)


@dataclass(frozen=True)
class Jet:
    value: Interval
    derivative: Interval

    @staticmethod
    def const(number):
        return Jet(Interval.const(number), Interval.const(0))

    @staticmethod
    def variable(lo, hi):
        return Jet(Interval.between(lo, hi), Interval.const(1))

    def __add__(self, other):
        other = as_jet(other)
        return Jet(self.value + other.value, self.derivative + other.derivative)

    __radd__ = __add__

    def __neg__(self):
        return Jet(-self.value, -self.derivative)

    def __sub__(self, other):
        return self + (-as_jet(other))

    def __rsub__(self, other):
        return as_jet(other) - self

    def __mul__(self, other):
        other = as_jet(other)
        return Jet(self.value * other.value,
                   self.derivative * other.value + self.value * other.derivative)

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = as_jet(other)
        return Jet(self.value / other.value,
                   (self.derivative*other.value - self.value*other.derivative)
                   / (other.value*other.value))

    def __rtruediv__(self, other):
        return as_jet(other) / self

    def sqrt(self):
        root = self.value.sqrt()
        require(root.lo > 0, 'DERIVATIVE_OF_ZERO_SQRT')
        return Jet(root, self.derivative / (2*root))


def as_jet(value):
    return value if isinstance(value, Jet) else Jet.const(value)


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)), Jet.const(0))


def sub(a,b):
    return [x-y for x,y in zip(a,b)]


def cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def quadric_center(q,t):
    a,b,g=q[4:7]
    determinant=b*g-t*t
    require(determinant.value.lo > 0 and a.value.lo > 0,
            'QUADRIC_NOT_POSITIVE_DEFINITE_ON_INTERVAL')
    return [-q[1]/(2*a), -(g*q[2]-t*q[3])/(2*determinant),
            -(-t*q[2]+b*q[3])/(2*determinant)]


def inverse_gauss_point(q,t,normal):
    """Exact algebraic fixed-normal ellipsoid surface x=C+sqrt(K/(n.M.n))*M.n.

    The direction `normal` is UN-normalized; its positive scale cancels.
    Returns a Jet with rigorously enclosed position and derivative.
    """
    a,b,g=q[4:7]
    determinant=b*g-t*t
    c=quadric_center(q,t)
    transformed=[normal[0]/a, (g*normal[1]-t*normal[2])/determinant,
                 (-t*normal[1]+b*normal[2])/determinant]
    k=-q[0]+(q[1]*q[1]/a+
              (g*q[2]*q[2]-2*t*q[2]*q[3]+b*q[3]*q[3])/determinant)/4
    require(k.value.lo>0, 'ELLIPSOID_LEVEL_INVALID')
    scale=(k/dot(normal,transformed)).sqrt()
    return [c[j]+scale*transformed[j] for j in range(3)]


def event_det(q, origin, design, normals, t):
    source24=[x+origin[j] for j,x in enumerate(inverse_gauss_point(q,t,normals[24]))]
    source90=[x+origin[j] for j,x in enumerate(inverse_gauss_point(q,t,normals[90]))]
    return dot(cross(sub(source90,source24), sub(design[0],source24)),
               sub(design[1],source24))


def digest_bytes(data):
    return sha256(data).hexdigest()


def load_evidence(archive):
    hasher=sha256()
    with archive.open('rb') as stream:
        for block in iter(lambda: stream.read(1<<20), b''):
            hasher.update(block)
    require(hasher.hexdigest()==ARTIFACT_SHA, 'ARTIFACT_ZIP_SHA_DRIFT')
    with zipfile.ZipFile(archive) as z:
        request_bytes=z.read('artifacts/h8-request/prepared-request.json')
        require(digest_bytes(request_bytes)==REQUEST_SHA, 'REQUEST_SHA_DRIFT')
        request=json.loads(request_bytes)
        report_bytes=z.read('artifacts/h8f-all81-points/report.json')
        report=json.loads(report_bytes)
        statuses=json.loads(z.read('artifacts/h8f-81-exact-construction-classification.json'))
        require(report['completed_samples']==81 and len(report['numeric_checks'])==30
                and report['all_numerical_checks_passed'] is True
                and report['qualified_branch_neighborhood'] is False
                and report['formal_newton_converged'] is False
                and report['input_request_sha256']==REQUEST_SHA
                and statuses['source_report_sha256']==digest_bytes(report_bytes)
                and statuses['classifications']=={
                    'CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE':1,
                    'SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED':79},
                'NOT_FROZEN_FAILED_H8F_EVIDENCE')
        samples={}
        for i in INDICES:
            prefix=f'artifacts/h8f-all81-points/point-{i:03d}'
            item=json.loads(z.read(prefix+'.json'))
            material_bytes=z.read(prefix+'-material.json.gz')
            require(digest_bytes(material_bytes)==item['exact_same_call_material_archive_sha256'],
                    f'POINT_{i}_MATERIAL_SHA_DRIFT')
            mat=json.loads(gzip.decompress(material_bytes))
            require(item['index']==i and item['coefficients']==mat['quadric_coefficients']
                    and item['feature_branch_hash']==mat['topology_hash']
                    and item['material_geometry_hash']==mat['geometry_hash']
                    and item['exact_native_material_boundary_passed'] is True
                    and str(mat['boolean_backend_identity']).startswith('cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'),
                    f'POINT_{i}_NOT_NATIVE_CLEAN')
            samples[i]=(item,mat)
    return request,report,samples


def binary_fraction_array(row):
    return [F.from_float(float(v)) for v in row]


def cjet(value):
    return [Jet.const(v) for v in value]


def normals_for_anchor(anchor,q,origin,samples):
    item,mat=samples[anchor]
    t=Jet.const(F.from_float(item['coefficients'][7]))
    center=quadric_center(q,t)
    # Extract exact-normal representative from the archived native binary64
    # sample: n=A(q)*(x-C). Positive overall scale is irrelevant.
    a,b,g=q[4:7]
    vectors={}
    for index in SOURCE_IDS:
        x=cjet(binary_fraction_array(mat['quadric_source_vertices'][index]))
        direction=sub(sub(x,origin),center)
        tval=t
        vectors[index]=[a*direction[0], b*direction[1]+tval*direction[2],
                        tval*direction[1]+g*direction[2]]
    return vectors


def source_fit(q,origin,samples,anchor_normals):
    worst=0
    worst_sample=None
    for sample in INDICES:
        item,mat=samples[sample]
        t=Jet.const(F.from_float(item['coefficients'][7]))
        for source_id in SOURCE_IDS:
            predicted=inverse_gauss_point(q,t,anchor_normals[source_id])
            measured=binary_fraction_array(mat['quadric_source_vertices'][source_id])
            for axis in range(3):
                discrepancy=predicted[axis].value+origin[axis].value-Interval.const(measured[axis])
                max_error=max(abs(discrepancy.lo),abs(discrepancy.hi))
                if max_error>worst:
                    worst=max_error
                    worst_sample=[sample,source_id,axis]
    return float(F(worst,SCALE)),worst_sample


def bisect(q,origin,design,normals,steps=44):
    lower,upper=LOW,HIGH
    require(event_det(q,origin,design,normals,Jet.const(lower)).value.sign()==1
            and event_det(q,origin,design,normals,Jet.const(upper)).value.sign()==-1,
            'SURROGATE_ANCHOR_DOES_NOT_BRACKET_EVENT')
    for _ in range(steps):
        middle=(lower+upper)/2
        d=event_det(q,origin,design,normals,Jet.const(middle))
        require(d.value.sign() in (-1,1), 'INDETERMINATE_EXACT_EVENT_SIGN')
        if d.value.sign()>0:lower=middle
        else:upper=middle
    return lower,upper


def solve(artifact):
    request, report, samples=load_evidence(artifact)
    req=request['request']
    require(req['target_axes']==[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
            and request['evidence']['scope']=='H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED',
            'SURROGATE_SUPPORTS_ONLY_FROZEN_IDENTITY_AXES_H8')
    qvalues=binary_fraction_array(report['target_q'])
    require(qvalues[7:]==[F(0),F(0),F(0)] and all(qvalues[i]>0 for i in (4,5,6)),
            'SURROGATE_ONLY_BASE_ZERO_OFFDIAGONALS')
    for i in INDICES:
        v=samples[i][0]['coefficients']
        require(all(F.from_float(v[j])==qvalues[j] for j in range(10) if j!=7),
                f'UNFROZEN_PARAMETER_COMPONENT_{i}')
        require(samples[i][1]['quadric_source_faces']==samples[0][1]['quadric_source_faces'],
                f'SOURCE_FACE_CONNECTIVITY_DRIFT_{i}')
    q=cjet(qvalues)
    origin=cjet(binary_fraction_array(req['target_origin']))
    design=[cjet(binary_fraction_array(req['design_vertices'][i])) for i in DESIGN_IDS]
    anchor0=normals_for_anchor(0,q,origin,samples)
    maxerr,worst=source_fit(q,origin,samples,anchor0)
    require(maxerr<2e-14, 'INVERSE_GAUSS_MODEL_DOES_NOT_REPRODUCE_ARCHIVED_SOURCE')
    t=Jet.variable(LOW,HIGH)
    d=event_det(q,origin,design,anchor0,t)
    require(d.derivative.sign()==-1, 'ANALYTIC_SURROGATE_MONOTONICITY_NOT_CERTIFIED')
    d_lo=event_det(q,origin,design,anchor0,Jet.const(LOW)).value
    d_hi=event_det(q,origin,design,anchor0,Jet.const(HIGH)).value
    require(d_lo.sign()==1 and d_hi.sign()==-1, 'ANALYTIC_SURROGATE_ROOT_NOT_BRACKETED')
    roots={}
    for sample in (0,57,59,60,62):
        lower,upper=bisect(q,origin,design,normals_for_anchor(sample,q,origin,samples))
        roots[str(sample)]={'lower':float(lower),'upper':float(upper)}
    lower,upper=bisect(q,origin,design,anchor0)
    mids=[(x['lower']+x['upper'])/2 for x in roots.values()]
    return {
        'schema':'heart-h9-offline-rational-interval-inverse-gauss-event-v1',
        'historic_run_id':39123384402,'historic_run_conclusion':'failure',
        'artifact_id':12135528290,'artifact_zip_sha256':ARTIFACT_SHA,
        'frozen_request_sha256':REQUEST_SHA,
        'archive_samples_verified':list(INDICES),'native_calls_performed_this_run':0,
        'surrogate':'FIXED_NORMAL_INVERSE_GAUSS_FROM_BINARY64_ARCHIVE_SEEDS_NOT_PRODUCTION_CHERCHI',
        'assumptions':['H8 fixed inverse-Gauss normals are continuous across bracket',
                       'source triangle identities do not switch inside bracket',
                       'roundoff between native source and archived binary64 seed is negligible; not formally bounded'],
        'matched_archived_source_vertices':list(SOURCE_IDS),
        'archived_coordinate_comparisons':len(INDICES)*len(SOURCE_IDS)*3,
        'max_model_vs_actual_archived_coordinate_absolute_error':maxerr,
        'worst_fit_sample_source_axis':worst,
        'rational_fixed_point_decimal_digits':38,
        'verified_surrogate_continuous_derivative_sign':d.derivative.sign(),
        'verified_surrogate_derivative_enclosure':d.derivative.as_floats(),
        'surrogate_endpoint_det_enclosures':{'low':d_lo.as_floats(),'high':d_hi.as_floats()},
        'surrogate_bisection_steps':44,
        'surrogate_root_bracket_binary64_anchor0':{'lower':float(lower),'upper':float(upper),
            'exact_lower_fraction':str(lower),'exact_upper_fraction':str(upper),
            'width_float':float(upper-lower)},
        'surrogate_root_estimates_other_native_binary64_anchors':roots,
        'surrogate_root_anchor_estimate_spread_float':max(mids)-min(mids),
        'conditional_surrogate_unique_root':True,
        'actual_native_cherchi_boolean_event_certified':False,
        'continuous_Cherchi_construction_stratum_certified':False,
        'actual_accepted_newton_step_observed':False,
        'newton_admitted':False,'final_heart_obj_produced':False,
        'actual_converged_newton_residual_available':False,
        'final_independently_integrated_physical_metrics_available':False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=solve(a.artifact)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as out:
        json.dump(result,out,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)
        out.write('\n')
    print('H9_RATIONAL_INTERVAL_SURROGATE_UNIQUE_ROOT_NEWTON_DENIED',json.dumps({
        'bracket':result['surrogate_root_bracket_binary64_anchor0'],
        'derivative':result['verified_surrogate_derivative_enclosure'],
        'max_source_fit_error':result['max_model_vs_actual_archived_coordinate_absolute_error'],
        'new_native_calls':result['native_calls_performed_this_run']},sort_keys=True))

if __name__=='__main__':main()
