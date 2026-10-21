"""W2 M17: reproduce three source primitives bit-for-bit; never a Cherchi teacher."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh

PINNED={
 'outer-ellipsoid':('1a7b1ae060fb3a8e4fa1c35cd9b2d1bdea44564c84bf9c360ec79c0f6bdaaa6f','f0f84a4ef147cc73cdca13a361c13da55a7ea28ef80b5e1a2f9f5a665427e4d6',642,1280),
 'hub-fixed':('4ae1fb276a80cf729e5b262d87c280c34e91daba4954892d4588030d0e7dfbbb','ea8a68686a28d43ca826032c785a546508a1252b2cc414510db9b2b1d0db157a',50,96),
 'pin-fixed':('97a2e7cf4da76bec888ca183de1f62b4d61f2055f8fab7515c251110c660f130','a5ba4a5d0e151f1edff6c375c806ead75e5cf1fec36e274213133b9cb8402a1b',530,1056),
}
ORIGINAL_MANIFEST_BLOB='f476a8c3e87bd30ef186b24442f641c2602c32ec'
ORIGINAL_CSG_BLOB='1e824c72d5ee13cc484bbf60a0be9b79be86d787'
CSG_HASHES={
'design':'48e8d3008bba746823eafd9c3704b52d597595b802066450a921ecc0dcb7f611',
'envelope':'92f46d68025467961fcc8b2b52353b4a18c2a981a09ad654ad6af3fb128b73fd',
'fixed':'71f9df91fca12fde4f4f2c80dc26e2d1229e8209e09db46e680d0de7baee264a',
'fixed-inside-envelope':'a944da4e36e5fe386cee3b28e4acf5800fc3942cde4eb35ba54f5de626f55dc7',
'fixed-outside-envelope':'8c66f71da99773fbc9a76b4f82fc43c55816df1876b643634ae64768f72ba262',
'initial':'640877647134a54152a8e1f63c1f356d752e6c66f7913301580c1e85a356d83b'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def blob(path):
 b=Path(path).read_bytes()
 return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def parts():
 outer=trimesh.creation.icosphere(subdivisions=3)
 outer.vertices=outer.vertices*np.array([.98,.82,.42])+np.array([0,0,.9])
 hub=trimesh.creation.cylinder(radius=.056,height=1.59-.21,sections=24)
 hub.apply_translation([0,0,(.21+1.59)/2])
 profile=[(0.,-.16),(.015,-.151),(.025,-.137),(.034,-.088),(.045,-.038),
          (.045,1.580),(.075,1.580),(.089,1.603),(.094,1.622),
          (.094,1.800),(.088,1.825),(.074,1.842),(.0,1.842)]
 pin=trimesh.creation.revolve(np.asarray(profile,float),sections=48)
 vertices=np.asarray(pin.vertices).copy();z=vertices[:,2];theta=np.arctan2(vertices[:,1],vertices[:,0]);radius=np.linalg.norm(vertices[:,:2],axis=1)
 selected=(z>1.59)&(z<1.835)&(radius>.07)
 scale=1.+.055*np.cos(12*theta)
 vertices[selected,:2]*=scale[selected,None];pin.vertices=vertices
 if pin.volume<0:pin.invert()
 return {'outer-ellipsoid':outer,'hub-fixed':hub,'pin-fixed':pin}

def write_obj(path,mesh):
 with Path(path).open('x',encoding='utf-8') as stream:
  for vertex in mesh.vertices:stream.write('v '+' '.join(format(float(v),'.17g') for v in vertex)+'\n')
  for face in mesh.faces:stream.write('f '+' '.join(str(int(v)+1) for v in face)+'\n')

def reproduce(path):
 out=Path(path);out.mkdir(parents=True,exist_ok=False);result={}
 for name,mesh in parts().items():
  expected_model,expected_si,nv,nf=PINNED[name]
  if not(mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0 and
         len(mesh.vertices)==nv and len(mesh.faces)==nf):
   raise ValueError('INVALID_SOURCE_PART:'+name)
  model=out/(name+'-model.obj');write_obj(model,mesh)
  si=mesh.copy();si.vertices*=.025
  si_path=out/(name+'-si.obj');write_obj(si_path,si)
  if sha(model)!=expected_model or sha(si_path)!=expected_si:
   raise ValueError('SOURCE_SHA_MISMATCH:'+name)
  result[name]={'model_sha256':expected_model,'si_sha256':expected_si,'vertices':nv,'faces':nf}
 return result

def inspect_full_source(path,manifest):
 if blob(manifest)!=ORIGINAL_MANIFEST_BLOB:raise ValueError('UNPINNED_94_PART_MANIFEST')
 obj=json.loads(Path(manifest).read_text());records=obj['parts'];fixed=obj['construction']['fixed_parts']
 if(len(records),len(fixed))!=(94,93) or set(fixed)!=set(records)-{'outer-ellipsoid'}:
  raise ValueError('SOURCE_RECIPE_CHANGED')
 matched=[];missing=[]
 for name,meta in records.items():
  for suffix in ('model','si'):
   p=Path(path)/meta[suffix+'_obj']
   if not p.is_file():missing.append(str(p));continue
   if sha(p)!=meta['sha256_'+suffix]:raise ValueError('SOURCE_FILE_DRIFT:'+name+':'+suffix)
   matched.append((name,suffix))
 return {'verified_files':len(matched),'missing_files':len(missing),'all_parts_verified':len(matched)==188,
         'native_Cherchi_teacher_admitted':False,'missing_paths':missing}

def inspect_csg(path,construction):
 if blob(construction)!=ORIGINAL_CSG_BLOB:raise ValueError('UNPINNED_CSG_RECEIPT')
 obj=json.loads(Path(construction).read_text());matched=[];missing=[]
 if obj['csg_executed_current_process']!=96 or obj['independent_partition_verified'] is not False:
  raise ValueError('HISTORICAL_CSG_SCOPE_CHANGED')
 for name,digest in CSG_HASHES.items():
  if obj['outputs'][name]['sha']!=digest:raise ValueError('CSG_RECEIPT_DRIFT:'+name)
  p=Path(path)/(name+'-rational.json')
  if not p.is_file():missing.append(name);continue
  if sha(p)!=digest:raise ValueError('CSG_PACKET_DRIFT:'+name)
  matched.append(name)
 return {'matched_historical_packets':matched,'missing_packets':missing,
         'all_historical_CSG_packets_present':len(matched)==6,
         'separate_rounded_F_D_A_certified':False,'new_native_teacher_admitted':False}
