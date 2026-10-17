"""Independent radial-cap numerical reference; NOT native material certification."""
import json
from pathlib import Path
import numpy as np

def matrix(q):
    q=np.asarray(q,dtype=float)
    if q.shape!=(10,) or not np.isfinite(q).all(): raise ValueError('INVALID_QUADRIC')
    return np.array([[q[4],q[9],q[8]],[q[9],q[5],q[7]],[q[8],q[7],q[6]]])

def branch(q,point):
    q=np.asarray(q,float);point=np.asarray(point,float)
    a=matrix(q)
    if point.shape!=(3,) or not np.isfinite(point).all():raise ValueError('INVALID_POINT')
    values,vectors=np.linalg.eigh(a);scale=max(1.,np.linalg.norm(a))
    if not(values[0]<0<values[2]):raise ValueError('INDEFINITE_REQUIRED')
    if min(abs(v) for v in values)<=1e-12*scale:raise ValueError('NEAR_SINGULAR')
    idx=2 if values[1]<0 else 0
    if min(abs(values[idx]-values[k]) for k in range(3) if k!=idx)<=1e-10*scale:
        raise ValueError('EIGENAXIS_NOT_SEPARATED')
    center=-.5*np.linalg.solve(a,q[1:4]);axis=vectors[:,idx].copy()
    offset=point-center
    signed=axis@offset
    if abs(signed)<=1e-12*max(1.,np.linalg.norm(offset)):raise ValueError('PROJECTION_NOT_SEPARATED')
    if signed<0:axis=-axis
    return a,center,values,vectors,idx,axis

def project(q,point,radius):
    if not np.isfinite(radius) or radius<=0:raise ValueError('INVALID_RADIUS')
    _,center,_,_,_,axis=branch(q,point)
    offset=np.asarray(point)-center
    return center+offset*(2*radius/(axis@offset))

def differential(q,point,radius,dq,dp):
    q,point,dq,dp=map(lambda x:np.asarray(x,dtype=float),(q,point,dq,dp))
    if dq.shape!=(10,) or dp.shape!=(3,) or not np.isfinite(dq).all() or not np.isfinite(dp).all():
        raise ValueError('INVALID_DIRECTION')
    if not np.isfinite(radius) or radius<=0:raise ValueError('INVALID_RADIUS')
    a,center,vals,vec,idx,axis=branch(q,point)
    da=matrix(dq);dc=-np.linalg.solve(a,da@center+dq[1:4]/2)
    raw=vec[:,idx]
    dax=sum(vec[:,k]*((vec[:,k]@da@raw)/(vals[idx]-vals[k])) for k in range(3) if k!=idx)
    if raw@(point-center)<0:dax=-dax
    delta=point-center;dx=dp-dc;den=axis@delta
    return dc+(2*radius/den)*dx-delta*(2*radius*(dax@delta+axis@dx)/den**2)

def run_isolated_check(q,point,radius,seed=0):
    rng=np.random.default_rng(seed);maximum=0.
    radial=np.linalg.norm(differential(q,point,radius,q,np.zeros(3)))
    for _ in range(10):
        dq=rng.normal(size=10);dq/=np.linalg.norm(dq);dp=rng.normal(size=3)
        analytic=differential(q,point,radius,dq,dp)
        for h in (1e-4,1e-5,1e-6):
            def f(t):return project(q+t*dq,point+t*dp,radius)
            numerical=(-f(2*h)+8*f(h)-8*f(-h)+f(-2*h))/(12*h)
            maximum=max(maximum,float(np.linalg.norm(numerical-analytic)/max(1.,np.linalg.norm(analytic))))
    if maximum>1e-6 or radial>1e-8:raise ValueError('ISOLATED_DIFFERENTIAL_FAILED')
    return dict(maximum_relative_error=maximum,scale_direction_norm=float(radial),
                native_source_derivative_passed=False,material_jacobian_passed=False,heart_newton_converged=False)

def main():
    root=Path(__file__).resolve().parent
    reg=json.loads((root/'heart-seed1-source-failure-registration-01.json').read_text())
    q=np.array(reg['event']['quadric_coefficients'])
    witness=json.loads((root/'heart-source-failure-replay-job-03/stdout.log').read_text())['error']
    fields=dict(a.split('=',1) for a in witness.split(';')[1:] if '=' in a)
    verts=np.array([[float(x) for x in row.split(',') if x] for row in fields['witness_vertices'].split('|') if row])
    print(json.dumps(run_isolated_check(q,verts[89],float(fields['truncation_radius'])),indent=2))
if __name__=='__main__':main()
