"""W2 pre-W0 fail-closed teacher label adapter. No native Cherchi call is implied."""
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

SCHEMA = "w2-cherchi-teacher-v1-pre-w0"
ORDER = ["m","x","y","z","xx","yy","zz","yz","xz","xy"]

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",",":"), allow_nan=False)

def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()

def vector(x):
    if not isinstance(x,(tuple,list)) or len(x)!=10:
        raise ValueError("TEN_COMPONENTS_REQUIRED")
    y=[float(v) for v in x]
    if not all(math.isfinite(v) for v in y):
        raise ValueError("NONFINITE_COMPONENT")
    return y

def seal(*,model_sha256,native_module_sha256,geometry,density,frame,q,
         r_d,j_d,r_f,topology_status,derivative_status,derivative_contract,
         stage_seconds,peak_rss_bytes,exact_proof,split,failure_reason=None):
    for s in (model_sha256,native_module_sha256):
        if not isinstance(s,str) or len(s)!=64 or any(c not in "0123456789abcdef" for c in s):
            raise ValueError("INVALID_SHA")
    q=vector(q)
    r_d=vector(r_d) if r_d is not None else None
    r_f=vector(r_f) if r_f is not None else None
    if j_d is not None:
        if not isinstance(j_d,list) or len(j_d)!=10:
            raise ValueError("J_SHAPE")
        j_d=[vector(row) for row in j_d]
    if (derivative_status!="VALID" and j_d is not None) or (
        derivative_status=="VALID" and (j_d is None or not derivative_contract or topology_status!="VALID")):
        raise ValueError("DERIVATIVE_NOT_ADMISSIBLE")
    if split not in ("train","val","test","excluded"):
        raise ValueError("INVALID_SPLIT")
    density=float(density)
    if not math.isfinite(density) or density<=0:
        raise ValueError("INVALID_DENSITY")
    if not isinstance(stage_seconds,dict) or any(
        not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in stage_seconds.values()):
        raise ValueError("INVALID_TIMINGS")
    if peak_rss_bytes is not None and (not isinstance(peak_rss_bytes,int) or peak_rss_bytes<0):
        raise ValueError("INVALID_MEMORY")
    p=dict(schema=SCHEMA,order=ORDER,coefficient_convention="NATIVE_MATRIX_ENTRY_Q10",
           model_sha256=model_sha256,native_module_sha256=native_module_sha256,
           geometry=geometry,density=density,frame=frame,q=q,r_D=r_d,J_D=j_d,r_F=r_f,
           topology_status=topology_status,derivative_status=derivative_status,
           derivative_contract=derivative_contract,stage_seconds=stage_seconds,
           peak_rss_bytes=peak_rss_bytes,exact_proof=exact_proof,split=split,
           failure_reason=failure_reason,
           total_policy="r_total=r_F+r_D;J_total=J_D;fixed_never_in_r_D")
    return dict(payload=p,payload_sha256=digest(p),identity=dict(
        q_sha256=digest(q),geometry_sha256=digest(geometry),
        model_sha256=model_sha256,native_module_sha256=native_module_sha256))

def verify(record,*,expected_q,expected_model_sha256,expected_native_module_sha256):
    if set(record)!={"payload","payload_sha256","identity"}:
        raise ValueError("INVALID_ENVELOPE")
    p=record["payload"]
    if p.get("schema")!=SCHEMA or p.get("order")!=ORDER or p.get("coefficient_convention")!="NATIVE_MATRIX_ENTRY_Q10":
        raise ValueError("SCHEMA_OR_ORDER_MISMATCH")
    if digest(p)!=record["payload_sha256"]:
        raise ValueError("PAYLOAD_TAMPERED")
    if p.get("q")!=vector(expected_q) or digest(p["q"])!=record["identity"].get("q_sha256"):
        raise ValueError("Q_MISMATCH")
    if p.get("model_sha256")!=expected_model_sha256 or p.get("native_module_sha256")!=expected_native_module_sha256:
        raise ValueError("MODULE_MISMATCH")
    expected=seal(model_sha256=p["model_sha256"],native_module_sha256=p["native_module_sha256"],
        geometry=p["geometry"],density=p["density"],frame=p["frame"],q=p["q"],r_d=p["r_D"],
        j_d=p["J_D"],r_f=p["r_F"],topology_status=p["topology_status"],
        derivative_status=p["derivative_status"],derivative_contract=p["derivative_contract"],
        stage_seconds=p["stage_seconds"],peak_rss_bytes=p["peak_rss_bytes"],
        exact_proof=p["exact_proof"],split=p["split"],failure_reason=p["failure_reason"])
    if record!=expected:
        raise ValueError("IDENTITY_OR_CANONICAL_MISMATCH")
    return p

def save(path,record):
    Path(path).write_text(canonical(record)+"\n",encoding="utf-8")

def load(path,*,expected_q,expected_model_sha256,expected_native_module_sha256):
    return verify(json.loads(Path(path).read_text(encoding="utf-8")),
        expected_q=expected_q,expected_model_sha256=expected_model_sha256,
        expected_native_module_sha256=expected_native_module_sha256)

def analytical_box_moments(bounds,density=1):
    """Independent exact rational closed-box reference, not native teacher data."""
    edges=[(Fraction(str(a)),Fraction(str(b))) for a,b in bounds]
    if len(edges)!=3 or any(b<=a for a,b in edges):
        raise ValueError("INVALID_BOX")
    def moment(px,py,pz):
        powers=(px,py,pz)
        value=Fraction(str(density))
        for (a,b),n in zip(edges,powers):
            value*=(b**(n+1)-a**(n+1))/(n+1)
        return value
    return [moment(*p) for p in ((0,0,0),(1,0,0),(0,1,0),(0,0,1),
        (2,0,0),(0,2,0),(0,0,2),(0,1,1),(1,0,1),(1,1,0))]
