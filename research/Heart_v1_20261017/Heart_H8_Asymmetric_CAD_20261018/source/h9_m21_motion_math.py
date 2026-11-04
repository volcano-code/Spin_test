"""W3 M21 exact retained-construction diagnostics; NOT a Boolean/Newton solver.

Positions and tangent transport are rational algebra on the saved constraints.
A tangent is only as authoritative as its supplied source-vertex velocity.
This module never invents a source velocity from a missing attachment.
"""
from __future__ import annotations
from collections import Counter
from fractions import Fraction as F
import math

NAMES = ('mass','Mx','My','Mz','Mxx','Myy','Mzz','Myz','Mxz','Mxy')
PAIRS = ((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))
ZERO = (F(0),)*3


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def frac(x):
    if isinstance(x, F):
        return x
    if type(x) in (int,float):
        need(math.isfinite(x), 'NONFINITE_COORDINATE')
        return F(x)
    need(type(x) is str and len(x)<100000, 'INVALID_RATIONAL_COORDINATE')
    from h9_m20_precision_replay import rational
    return rational(x)


def vec(row):
    need(isinstance(row,(list,tuple)) and len(row)==3,'BAD_VECTOR3')
    return tuple(frac(x) for x in row)


def add(a,b): return tuple(x+y for x,y in zip(a,b))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def mul(k,a): return tuple(k*x for x in a)
def dot(a,b): return sum((x*y for x,y in zip(a,b)),F(0))
def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def solve3(rows, rhs):
    a=[list(vec(row))+[frac(b)] for row,b in zip(rows,rhs)]
    need(len(a)==3, 'BAD_LINEAR_SYSTEM')
    for i in range(3):
        pivot=next((k for k in range(i,3) if a[k][i]),None)
        need(pivot is not None, 'SINGULAR_RETAINED_CONSTRAINT')
        a[i],a[pivot]=a[pivot],a[i]
        d=a[i][i];a[i]=[x/d for x in a[i]]
        for j in range(3):
            if j!=i:
                c=a[j][i];a[j]=[x-c*y for x,y in zip(a[j],a[i])]
    return tuple(a[i][3] for i in range(3))


def plane(p, v):
    a,b,c=p;va,vb,vc=v
    u,w=sub(b,a),sub(c,a)
    n=cross(u,w)
    dn=add(cross(sub(vb,va),w),cross(u,sub(vc,va)))
    return n,dot(n,a),dn,dot(dn,a)+dot(n,va)


def construction(kind, positions, velocities):
    """Independent analytic derivative of EXPLICIT/LPI/TPI constraints.

    Exactly singular systems are rejected. No conditioning or interval
    smoothness certificate is inferred from a nonzero exact determinant.
    """
    p=[vec(x) for x in positions];v=[vec(x) for x in velocities]
    count={'EXPLICIT3D':1,'LPI':5,'TPI':9}.get(kind)
    need(count is not None and len(p)==len(v)==count,'UNSUPPORTED_CONSTRUCTION')
    if kind=='EXPLICIT3D': return p[0],v[0]
    if kind=='LPI':
        a,b=p[:2];va,vb=v[:2]
        n,_,dn,_=plane(p[2:],v[2:])
        u=sub(b,a);du=sub(vb,va);w=sub(p[2],a);dw=sub(v[2],va)
        d=dot(n,u);nd=dot(n,w)
        need(d!=0,'SINGULAR_RETAINED_CONSTRAINT')
        dd=dot(dn,u)+dot(n,du);dnd=dot(dn,w)+dot(n,dw)
        t=nd/d;dt=(dnd*d-nd*dd)/(d*d)
        return add(a,mul(t,u)),add(va,add(mul(dt,u),mul(t,du)))
    planes=[plane(p[i:i+3],v[i:i+3]) for i in (0,3,6)]
    x=solve3([t[0] for t in planes],[t[1] for t in planes])
    dx=solve3([t[0] for t in planes],[t[3]-dot(t[2],x) for t in planes])
    return x,dx


def key_for(kind, operands):
    keys=[]
    for operand in operands:
        choices=operand.get('source_vertices')
        need(operand.get('status')=='UNIQUE' and type(choices) is list and len(choices)==1,
             'AMBIGUOUS_OR_MISSING_OPERAND')
        o=choices[0].get('input_object');i=choices[0].get('input_vertex')
        need(type(o) is int and o in (0,1) and type(i) is int and i>=0,'INVALID_OPERAND_ID')
        keys.append((o,i))
    need(len(keys)=={'EXPLICIT3D':1,'LPI':5,'TPI':9}.get(kind),'UNSUPPORTED_CONSTRUCTION')
    if kind=='EXPLICIT3D': return kind,tuple(keys)
    if kind=='LPI':return kind,tuple(sorted(keys[:2])),tuple(sorted(keys[2:]))
    return kind,tuple(sorted(tuple(sorted(keys[i:i+3])) for i in (0,3,6)))


def to_target(p,request,velocity=False):
    axes=[vec(x) for x in request['target_axes']]
    origin=ZERO if velocity else vec(request['target_origin'])
    shifted=sub(p,origin)
    return tuple(sum((shifted[i]*axes[i][j] for i in range(3)),F(0)) for j in range(3))


def material_state(material, request, source_velocity=None):
    """Rebuild every saved physical point; bind operands to frozen input IDs.

    H9 normalization is the original L=1, origin=0 experiment. Its target
    affine transform is checked exactly against every saved target point.
    Missing source velocity leaves motion UNKNOWN, never all-zero by default.
    """
    proof=material['material_proof']
    need(proof.get('schema')=='cherchi-same-call-material-v1','BAD_MATERIAL_PROOF')
    src=[vec(x) for x in material['quadric_source_vertices']]
    design=[vec(x) for x in request['design_vertices']]
    physical=[vec(x) for x in proof['exact_vertices']]
    target=[vec(x) for x in material['variable_rational_vertices']]
    raw=proof['construction_records'];resolved=proof['resolved_construction_records']
    n=len(physical)
    need(len(target)==len(raw)==len(resolved)==n and n>=4,'INCOMPLETE_CONSTRUCTION_COVERAGE')
    if source_velocity is not None:
        need(len(source_velocity)==len(src),'SOURCE_VELOCITY_LENGTH_MISMATCH')
        source_velocity=[vec(x) for x in source_velocity]
    def index_records(records):
        result={}
        for r in records:
            i=r.get('vertex_index')
            need(type(i) is int and 0<=i<n and i not in result,'DUPLICATE_OR_INVALID_VERTEX_SLOT')
            result[i]=r
        return result
    raw,resolved=index_records(raw),index_records(resolved)
    positions={};motion={} if source_velocity is not None else None
    slotkeys=[];kinds=Counter()
    for i in range(n):
        r,s=raw[i],resolved[i];kind=r['point_type']
        need(s.get('point_type')==kind,'RAW_RESOLVED_TYPE_MISMATCH')
        key=key_for(kind,s['operands']);slotkeys.append(key)
        need(key not in positions,'DUPLICATE_RETAINED_CONSTRAINT_KEY')
        pts=[vec(x) for x in r['operand_coordinates_exact']]
        need(len(pts)==len(s['operands']),'OPERAND_COUNT_MISMATCH')
        vel=[]
        for p,operand in zip(pts,s['operands']):
            q=operand['source_vertices'][0];obj,idx=q['input_object'],q['input_vertex']
            table=(design,src)[obj]
            need(idx<len(table) and p==table[idx],'OPERAND_NOT_BOUND_TO_ACTUAL_INPUT')
            vel.append(source_velocity[idx] if obj==1 and source_velocity is not None else ZERO)
        x,v=construction(kind,pts,vel)
        need(x==physical[i],'EXACT_CONSTRUCTION_POSITION_MISMATCH:'+str(i))
        tx=to_target(x,request)
        need(tx==target[i],'TARGET_FRAME_OR_NORMALIZATION_MISMATCH:'+str(i))
        positions[key]=tx
        if motion is not None:motion[key]=to_target(v,request,True)
        kinds[kind]+=1
    faces=material['variable_faces'];semantic=[]
    edges=Counter()
    for f in faces:
        need(type(f) is list and len(f)==3 and len(set(f))==3 and
             all(type(i) is int and 0<=i<n for i in f),'BAD_MATERIAL_FACE')
        t=tuple(slotkeys[i] for i in f)
        semantic.append(min(t,t[1:]+t[:1],t[2:]+t[:2]))
        for a,b in ((f[0],f[1]),(f[1],f[2]),(f[2],f[0])):edges[a,b]+=1
    need(all(c==1 and edges[b,a]==1 for (a,b),c in edges.items()),'OPEN_OR_MISORIENTED_CHAIN')
    return {'positions':positions,'motion':motion,'slotkeys':slotkeys,'faces':faces,
            'semantic_triangles':Counter(semantic),'source':src,'source_faces':material['quadric_source_faces'],
            'c7':float(material['quadric_coefficients'][7]),'kinds':dict(kinds),
            'source_motion_available':source_velocity is not None}


class Sum:
    """Balanced rational reduction; no float conversion in accumulation."""
    def __init__(self):self.levels=[]
    def add(self,x):
        if not x:return
        i=0
        while i<len(self.levels) and self.levels[i] is not None:
            x+=self.levels[i];self.levels[i]=None;i+=1
        if i==len(self.levels):self.levels.append(x)
        else:self.levels[i]=x
    def total(self):return sum((v for v in self.levels if v is not None),F(0))


def moment_tangent(state,density=1):
    """Independent derivative of signed tetrahedron raw-moment polynomials.

    Unlike production Reynolds coefficients this directly differentiates
    determinant and polynomial factors. Same supplied velocities, not an
    independent truth source for source motion.
    """
    need(state['motion'] is not None,'SOURCE_VELOCITY_NOT_AVAILABLE')
    out=[Sum() for _ in range(10)];active=0
    for face in state['faces']:
        keys=[state['slotkeys'][i] for i in face]
        a,b,c=[state['positions'][k] for k in keys]
        va,vb,vc=[state['motion'][k] for k in keys]
        if not any(va+vb+vc):continue
        active+=1
        det=dot(a,cross(b,c))
        dd=dot(va,cross(b,c))+dot(a,cross(vb,c))+dot(a,cross(b,vc))
        out[0].add(dd/6)
        sm=add(add(a,b),c);ds=add(add(va,vb),vc)
        for i in range(3):out[1+i].add((dd*sm[i]+det*ds[i])/24)
        for k,(i,j) in enumerate(PAIRS):
            diag=sum((p[i]*p[j] for p in (a,b,c)),F(0))
            ddiag=sum((v[i]*p[j]+p[i]*v[j] for p,v in ((a,va),(b,vb),(c,vc))),F(0))
            f=sm[i]*sm[j]+diag;df=ds[i]*sm[j]+sm[i]*ds[j]+ddiag
            out[4+k].add((dd*f+det*df)/120)
    return [x.total()*frac(density) for x in out],active


def compare_vectors(actual, reference, names=NAMES):
    need(len(actual)==len(reference)==len(names),'COMPARISON_DIMENSION')
    result={}
    for name,a,b in zip(names,actual,reference):
        a,b=frac(a),frac(b);r=a-b
        result[name]={'value':float(a),'reference':float(b),'signed_difference':float(r),
                      'absolute_difference':float(abs(r)),
                      'scaled_difference':float(abs(r)/max(F(1),abs(b))),
                      'relative_difference_if_nonzero':float(abs(r)/abs(b)) if b else None}
    return {'components':result,'max_scaled_difference':max(x['scaled_difference'] for x in result.values()),
            'comparison_is_diagnostic_not_admission':True}


def motion_pair(a,b):
    h=F(b['c7'])-F(a['c7']);need(h>0,'BAD_INTERVAL_ORDER')
    same=(a['positions'].keys()==b['positions'].keys() and
          a['semantic_triangles']==b['semantic_triangles'])
    out={'delta_c7':float(h),'same_retained_constraints_and_oriented_triangles':same,
         'continuous_neighborhood_certified':False,'newton_admitted':False}
    if not same:
        out['status']='FEATURE_CHANGED_NO_VERTEX_MOTION_COMPARISON';return out
    # Boundary keys, not row indices, establish correspondence.
    per_kind={}
    for key,pa in a['positions'].items():
        pb=b['positions'][key]
        row=per_kind.setdefault(key[0],{'vertex_count':0,'max_displacement':0.,
                                      'max_secant_vs_average_motion':None,'worst_constraint':None})
        row['vertex_count']+=1
        row['max_displacement']=max(row['max_displacement'],max(float(abs(x)) for x in sub(pb,pa)))
        if a['motion'] is not None and b['motion'] is not None:
            average=mul(F(1,2),add(a['motion'][key],b['motion'][key]))
            error=max(abs(x-y) for x,y in zip(mul(1/h,sub(pb,pa)),average))
            if row['max_secant_vs_average_motion'] is None or float(error)>row['max_secant_vs_average_motion']:
                row['max_secant_vs_average_motion']=float(error);row['worst_constraint']=repr(key)
    out.update(status='FINITE_PAIR_GEOMETRY_COMPARED',construction_groups=per_kind,
               motion_available=a['motion'] is not None and b['motion'] is not None)
    return out
