"""Integrate authoritative v7 exact rational fixed solid; no solver assumptions."""
from pathlib import Path
import json,hashlib,time,traceback,sys
import numpy as np
import _cherchi_rational_moments as gmp
R=Path(__file__).resolve().parent;P=R/'exact_v7c/fixed-rational.json';Q=R/'fixed-v7-GMP-exact-moments.json'
t=time.monotonic();rep={'status':'STARTED','source_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'module_sha256':hashlib.sha256(Path(gmp.__file__).read_bytes()).hexdigest(),'units':'model length with unit density'}
try:
 d=json.loads(P.read_text());faces=np.asarray(d['faces'],dtype=np.int64)
 print('START_GMP',len(d['vertices']),len(faces),'after',time.monotonic()-t,flush=True)
 values=gmp.integrate_moments(d['vertices'],faces,1.)
 rep.update(status='COMPLETE',mass_moments=[float(x) for x in values],elapsed_seconds=time.monotonic()-t)
 print('COMPLETE',rep['mass_moments'],'seconds',rep['elapsed_seconds'],flush=True)
except BaseException as e:
 rep.update(status='FAILED',error=type(e).__name__+': '+str(e),traceback=traceback.format_exc(),elapsed_seconds=time.monotonic()-t)
 print('FAILED',rep['error'],flush=True)
finally:Q.write_text(json.dumps(rep,indent=2))
