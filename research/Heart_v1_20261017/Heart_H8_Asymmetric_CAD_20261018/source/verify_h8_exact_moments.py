"""Independent *exact* raw moment verifier for a captured H8 Cherchi packet.

Compare Python Fraction's oriented tetrahedron integrals to a separately
implemented compiled GMP surface integral, for all 10 mass monomials. No
floating point geometry replacement, no Newton or dynamics admission.
"""
from __future__ import annotations
from fractions import Fraction as F
from hashlib import sha256
import argparse
import gzip
import json
from pathlib import Path
import time
import numpy as np

PAIRS=((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))
BACKEND="cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1"

def file_sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def exact(token):
    if not isinstance(token,str):raise ValueError("NON_STRING_EXACT_TOKEN")
    parts=token.split("/")
    if len(parts)!=2:raise ValueError("BAD_RATIONAL_PAIR")
    def parse(value,negative=False):
        s=-1 if negative and value.startswith("-") else 1
        text=value[1:] if s<0 else value
        base=2 if text.startswith("0b") else 10
        digits=text[2:] if base==2 else text
        valid="01" if base==2 else "0123456789"
        if not digits or any(c not in valid for c in digits):
            raise ValueError("BAD_EXACT_INTEGER")
        return s*int(digits,base)
    n=parse(parts[0],True);d=parse(parts[1])
    if d<=0:raise ValueError("NONPOSITIVE_DENOMINATOR")
    return F(n,d)

def independent_ten_raw_moments(vertices,faces):
    """Oriented exact closed-surface tetrahedron integration at world origin.

    10 outputs: V,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY. This uses independent
    tetrahedral integration, not the native GMP surface-divergence code.
    """
    points=tuple(tuple(exact(token) for token in row) for row in vertices)
    result=[F(0) for _ in range(10)]
    for face in faces:
        if len(face)!=3 or any(type(i) is not int or i<0 or i>=len(points) for i in face):
            raise ValueError("INVALID_EXACT_FACE")
        a,b,c=[points[i] for i in face]
        det=a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0])
        if det==0:continue
        result[0]+=det/6
        sm=tuple(a[i]+b[i]+c[i] for i in range(3))
        for i in range(3):result[i+1]+=det*sm[i]/24
        for k,(i,j) in enumerate(PAIRS):
            diagonal=a[i]*a[j]+b[i]*b[j]+c[i]*c[j]
            result[k+4]+=det*(sm[i]*sm[j]+diagonal)/120
    return tuple(result)

def verify(packet_path,request_path,output):
    import _cherchi_rational_moments as arithmetic
    packet_path=Path(packet_path);request_path=Path(request_path);output=Path(output)
    if output.exists():raise FileExistsError("EXISTING_MOMENT_CERTIFICATE")
    with gzip.open(packet_path,"rt",encoding="utf8") as reader:packet=json.load(reader)
    request_json=json.loads(request_path.read_text())
    if packet.get("backend")!=BACKEND or request_json.get("schema")!="spin-heart-h8-faster-preparation-v1":
        raise ValueError("NOT_FROZEN_H8_CHERCHI_PACKET")
    evidence=request_json["evidence"]
    if (evidence.get("scope")!="H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED"
        or evidence.get("original_author_cad") is not False
        or evidence.get("newton_converged") is not False):
        raise ValueError("FROZEN_H8_SCOPE_NOT_VERIFIED")
    coords=packet["exact_vertices"];faces=packet["faces"]
    if len(coords)<4 or len(faces)<4:raise ValueError("EMPTY_CHERCHI_PACKET")
    started=time.perf_counter()
    python_values=independent_ten_raw_moments(coords,faces)
    python_elapsed=time.perf_counter()-started
    if python_values[0]<=0:raise ValueError("NEGATIVE_OR_NONPOSITIVE_VARIABLE_MASS")
    started=time.perf_counter()
    # GMP base-0 parser handles "0b" directly; preserve exact Cherchi strings.
    gmp=np.asarray(arithmetic.integrate_moments(
        coords,np.asarray(faces,dtype=np.int64),1.0),dtype=float)
    gmp_elapsed=time.perf_counter()-started
    if gmp.shape!=(10,) or not np.isfinite(gmp).all():
        raise ValueError("BAD_NATIVE_GMP_MOMENTS")
    independent=np.asarray([float(x) for x in python_values])
    ulps=np.spacing(np.maximum(np.abs(gmp),1.))
    max_ulps=float(np.max(np.abs(independent-gmp)/ulps))
    if max_ulps>4:raise ValueError("PYTHON_EXACT_VS_NATIVE_GMP_MOMENTS_DISAGREE")
    req=request_json["request"]
    fixed=np.asarray(req["fixed_shell_moments"],dtype=float)
    if fixed.shape!=(10,) or not np.isfinite(fixed).all():
        raise ValueError("INVALID_REGISTERED_FIXED_SHELL_MOMENTS")
    total=gmp+fixed
    if total[0]<=0:raise ValueError("INVALID_TOTAL_MASS")
    scale_m=float(req["original_units_per_normalized_unit"])
    density=float(evidence["density_kg_m3"])
    com=total[1:4]/total[0]
    report=dict(schema="h8c-exact-ten-mass-moment-double-implementation-v1",
        scope="H8_NONAUTHOR_CAD_ONE_QUADRIC_NOT_DERIVATIVE_OR_NEWTON",
        verified_actual_packet_sha256=file_sha(packet_path),
        frozen_request_sha256=file_sha(request_path),
        pure_python_fraction_vs_native_gmp_max_ulp=max_ulps,
        variable_raw_ten_moments_normalized=gmp.tolist(),
        total_raw_ten_moments_normalized=total.tolist(),
        total_mass_g=float(total[0]*density*scale_m**3*1000),
        center_of_mass_model=com.tolist(),
        center_of_mass_radial_offset_mm=float(np.linalg.norm(com[:2])*scale_m*1000),
        triangles=len(faces),vertices=len(coords),
        python_fraction_seconds=python_elapsed,native_gmp_seconds=gmp_elapsed,
        exact_ten_moments_independently_reproduced=True,
        full_jacobian_passed=False,newton_converged=False,
        contact_dynamics_certified=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("H8_EXACT_TEN_MOMENTS",json.dumps({
       k:report[k] for k in ("triangles","vertices","total_mass_g",
       "center_of_mass_radial_offset_mm","pure_python_fraction_vs_native_gmp_max_ulp",
       "python_fraction_seconds","native_gmp_seconds")}),flush=True)
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--packet",type=Path,required=True)
    p.add_argument("--request",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();verify(a.packet,a.request,a.output)
