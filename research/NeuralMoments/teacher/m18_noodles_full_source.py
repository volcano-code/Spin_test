"""W2 M18: deterministic Noodles V7 94-part source regenerator, not CSG or teacher.

Reimplements ONLY the frozen numeric source mesh construction from main's pinned
noodles_paper_geometry_v7.py, noodles_dense_v3_input.py, noodles_input.py.
Each output must match an externally observed SHA (not one computed by this code)
before any saved-source identity can be asserted. A source face is not a solid
Boolean/F/D/A partition; this program cannot produce training Jacobians.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import os
import numpy as np
import trimesh
import m17_core_sha_reconstruction as core

FULL_FROZEN_188_SHA_AND_94_COUNTS_DIGEST='6b2da86949e4426986e2460167f1255f0c44d6e708be87bfec17fb78ce4a69c6'
FROZEN_GENERATOR_BLOBS = {
 'v7':'73f78e76100139184318131eb7cff9816384bc7c',
 'v5':'a1d18dfd010f415cadc98990060796bc2d15d0c8',
 'v3':'3231deef019d676cb86bdcce7f54de90dd6d7256',
 'tube':'afc9a90bf5263a868038ea5ae66581941c6dfd3b',
 'manifest':'f476a8c3e87bd30ef186b24442f641c2602c32ec',
}
PREDECLARED_SAMPLES={
 'tube-000-fixed':('0026a63c3bd09e9cea8f2e6a69cb2919da2b5ca362fa0bf2c507b67f057d0c21','66bac7d2e4eb796915ae30c335f0a1937b21afcc5b7fed1bceb604ac8fb91b02'),
 'tube-038-fixed':('724c334cf3434c3ae9f5bb031cca9ce212a832e1cbddbfa4d677a8300c0d1b37','19e84d6e880cda2fbbcc6cc13fcc27cd9d659ddac57c4a1778adb6b4c279b5b0'),
 'tube-078-fixed':('3e26ae06ff5eaf54356b8ee5c0ecba634fd41e9c181f45b294907b1ddf398e0c','5ba5eef7ed68634c7649e5718b6edaf73aa28de42fb99ef973d5ea58f7578e12'),
 'rib-row-00-fixed':('40f667dfbfa2bd8f68713208fd7544f64ad7f052f3a3b45a5a1837bdb39c5cc3','ca5844cebbb65c491fc9f238cf696287aa0eb513fc70dc18d66992730f1c75f3'),
 'rib-row-05-fixed':('44bfac1b0d55be6352e7fd8033ecbcc46433661dc6fe8eedca873a907ee52c90','3fb5d2ffde2d43e67e9138827095ba37fcfca8783ab9e78b41fe4c55db75ff2a'),
 'rib-row-10-fixed':('81fff31d9c4e8070320bc77afeab63e213453a998e231e98b17f04b1257e4d59','b98b0310a9b216fbb2159ed53dc5109bf76512d511e482e2d69208e2833f9bce'),
 'rib-axial-fixed':('dd46270bf2b79d910552b93a36f5479bab7f70e4f8177b19361ce327adfd6cc4','d6dd468b1b6d10b999f6e41f6de3ad36548e18b4c1203348aee86df61864ecff'),
}


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()


def layout():
 # Immutable v3 layout used by v7 through v5 -> v3, NOT v7 flattened radii.
 radii=np.asarray([.98,.82,.70]);rows=[]
 for z in np.linspace(-(.57/.65*.70),(.57/.65*.70),11):
  for y in np.linspace(-(.66/.80*.82),(.66/.80*.82),9):
   level=(y/radii[1])**2+(z/radii[2])**2
   if level<.88:
    rows.append(dict(y_model=float(y),z_model=float(.90+z),
     half_length_model=float(radii[0]*np.sqrt(1-level)+.035)))
 if len(rows)!=79:raise ValueError('ORIGINAL_V3_LAYOUT_COUNT_CHANGED')
 return rows


def centerline(index:int):
 row=layout()[index]
 u=np.linspace(0.,1.,33);s=2*u-1;phase=.37*index
 x=s*row['half_length_model'];y0=row['y_model']
 y=(y0*(.78+(1-.78)*s*s)+
    .034*np.sin(2*np.pi*u+phase)*np.sin(np.pi*u)+
    .011*np.sin(6*np.pi*u+.17*index)*np.sin(np.pi*u))
 z=.90+.60*(row['z_model']-.90)+.018*np.sin(4*np.pi*u+.29*index)*np.sin(np.pi*u)
 return np.column_stack((x,y,z))


def tube_mesh(points,radius,sections):
 # Original parallel-transport circular rings; order is part of frozen OBJ SHA.
 points=np.asarray(points,dtype=float)
 tangent=np.gradient(points,axis=0)
 tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 seed=np.eye(3)[np.argmin(np.abs(tangent[0]))]
 normal=seed-seed.dot(tangent[0])*tangent[0]
 normal/=np.linalg.norm(normal)
 normals=[normal]
 for a,b in zip(tangent[:-1],tangent[1:]):
  axis=np.cross(a,b);sine=np.linalg.norm(axis);cosine=np.clip(a.dot(b),-1.,1.)
  if sine>1e-14:
   axis/=sine
   normal=normal*cosine+np.cross(axis,normal)*sine+axis*axis.dot(normal)*(1-cosine)
  normal-=normal.dot(b)*b;normal/=np.linalg.norm(normal)
  normals.append(normal.copy())
 normals=np.asarray(normals);binormals=np.cross(tangent,normals)
 angles=np.arange(sections)*2*np.pi/sections
 rings=points[:,None,:]+radius*(np.cos(angles)[None,:,None]*normals[:,None,:]+np.sin(angles)[None,:,None]*binormals[:,None,:])
 vertices=np.vstack((rings.reshape(-1,3),points[[0,-1]]))
 faces=[]
 for i in range(len(points)-1):
  for j in range(sections):
   a=i*sections+j;b=i*sections+(j+1)%sections
   c=(i+1)*sections+j;d=(i+1)*sections+(j+1)%sections
   faces.extend(((a,b,d),(a,d,c)))
 cap0,cap1=len(vertices)-2,len(vertices)-1
 for j in range(sections):
  k=(j+1)%sections
  faces.extend(((cap0,k,j),(cap1,(len(points)-1)*sections+j,(len(points)-1)*sections+k)))
 mesh=trimesh.Trimesh(vertices,np.asarray(faces),process=False)
 if mesh.volume<0:mesh.invert()
 return mesh


def rounded_tube(points,radius,sections):
 base=tube_mesh(points,radius,sections)
 rings=base.vertices[:-2].reshape(len(points),sections,3)
 tangent=np.gradient(points,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 theta=np.linspace(0,np.pi/2,4+2)[1:-1]
 first=[points[0]-radius*np.sin(t)*tangent[0]+np.cos(t)*(rings[0]-points[0]) for t in theta[::-1]]
 last=[points[-1]+radius*np.sin(t)*tangent[-1]+np.cos(t)*(rings[-1]-points[-1]) for t in theta]
 all_rings=np.asarray(first+list(rings)+last)
 vertices=np.vstack((all_rings.reshape(-1,3),points[0]-radius*tangent[0],points[-1]+radius*tangent[-1]))
 faces=[]
 for i in range(len(all_rings)-1):
  for j in range(sections):
   a=i*sections+j;b=i*sections+(j+1)%sections;c=(i+1)*sections+j;d=(i+1)*sections+(j+1)%sections
   faces.extend(((a,b,d),(a,d,c)))
 start,end=len(vertices)-2,len(vertices)-1
 for j in range(sections):
  k=(j+1)%sections;last_ring=(len(all_rings)-1)*sections
  faces.extend(((start,k,j),(end,last_ring+j,last_ring+k)))
 mesh=trimesh.Trimesh(vertices,np.asarray(faces),process=False)
 if mesh.volume<0:mesh.invert()
 return mesh


def rib_centerlines():
 rows=layout()
 levels=sorted(set(round(row['z_model'],12) for row in rows))
 out={}
 for k,z_orig in enumerate(levels):
  members=[i for i,row in enumerate(rows) if abs(row['z_model']-z_orig)<1e-9]
  centers=np.asarray([centerline(i)[len(centerline(i))//2] for i in members])
  lowest=float(centers[:,1].min())-.026
  highest=float(centers[:,1].max())+.026
  z=.90+.60*(z_orig-.90)
  out[f'rib-row-{k:02d}-fixed']=np.column_stack((np.zeros(17),np.linspace(lowest,highest,17),np.full(17,z)))
 zlo=.90+.60*(levels[0]-.90)
 zhi=.90+.60*(levels[-1]-.90)
 out['rib-axial-fixed']=np.column_stack((np.zeros(45),np.zeros(45),np.linspace(zlo-.025,zhi+.025,45)))
 if len(out)!=12:raise ValueError('RIB_COUNT_CHANGED')
 return out


def remaining():
 # 3 core sources from M17; all remaining are 79 tendrils + 12 ribs.
 rows=layout();parts={}
 for i in range(len(rows)):
  parts[f'tube-{i:03d}-fixed']=rounded_tube(centerline(i),.030,12)
 for name,points in rib_centerlines().items():
  radius=.022 if name=='rib-axial-fixed' else .017
  parts[name]=rounded_tube(points,radius,12)
 if len(parts)!=91:raise ValueError('WRONG_REMAINING_PART_COUNT')
 return parts


def mesh_certificate(mesh):
 # Necessary topology only. This is not self-intersection or Boolean admission.
 return dict(vertices=len(mesh.vertices),faces=len(mesh.faces),watertight=bool(mesh.is_watertight),
  winding_consistent=bool(mesh.is_winding_consistent),signed_volume=float(mesh.volume),
  components=len(mesh.split(only_watertight=False)))


def regenerate(dest, *,all_core=True):
 dest=Path(dest);dest.mkdir(parents=True,exist_ok=False)
 meshes=(dict(core.parts()) if all_core else {})
 meshes.update(remaining());ledger={}
 for name,mesh in meshes.items():
  shape=mesh_certificate(mesh)
  if not(shape['watertight'] and shape['winding_consistent'] and shape['signed_volume']>0 and shape['components']==1):
   raise ValueError('INVALID_INDEPENDENT_SOURCE_TOPOLOGY:'+name)
  mdl=dest/(name+'-model.obj');core.write_obj(mdl,mesh)
  si=mesh.copy();si.vertices*=.025
  actual=dest/(name+'-si.obj');core.write_obj(actual,si)
  h=sha(mdl);hsi=sha(actual)
  required=core.PINNED.get(name,PREDECLARED_SAMPLES.get(name))
  if required and (h,hsi)!=(required[0],required[1]):
   raise ValueError('HISTORICAL_PART_SHA_DRIFT:'+name+':'+h+'/'+hsi)
  ledger[name]={**shape,'model_sha256':h,'si_sha256':hsi,'model_obj':mdl.name,'si_obj':actual.name,
    'historical_hash_sample_verified':bool(required)}
 full_source_sha=corpus_identity_sha(ledger)
 if full_source_sha != FULL_FROZEN_188_SHA_AND_94_COUNTS_DIGEST:
  raise ValueError('HISTORICAL_188_SOURCE_SHA_OR_COUNTS_DRIFT:'+full_source_sha)
 return ledger


def corpus_identity_sha(ledger):
 payload=''.join(f'{name}\t{row["model_sha256"]}\t{row["si_sha256"]}\t{row["vertices"]}\t{row["faces"]}\n'
   for name,row in sorted(ledger.items()))
 return hashlib.sha256(payload.encode('ascii')).hexdigest()


def validate_against_original_manifest(ledger,source_manifest):
 # Unlike 'regenerate', this checks *all* 188 actual regenerated SHA against
 # externally pinned original historic bytes; caller must provide the manifest.
 raw=Path(source_manifest).read_bytes()
 header=b'blob '+str(len(raw)).encode()+b'\x00'
 if hashlib.sha1(header+raw).hexdigest()!=FROZEN_GENERATOR_BLOBS['manifest']:
  raise ValueError('HISTORICAL_MANIFEST_GIT_BLOB_CHANGED')
 historic=json.loads(raw);parts=historic['parts']
 if len(parts)!=len(ledger)!=94 or len(historic['construction']['fixed_parts'])!=93:
  raise ValueError('NOT_ALL_SOURCE_PARTS')
 for name,ref in parts.items():
  if name not in ledger:raise ValueError('MISSING_SOURCE_PART:'+name)
  for attr in ('model','si'):
   if ledger[name][attr+'_sha256']!=ref['sha256_'+attr]:
    raise ValueError('SOURCE_SHA_MISMATCH:'+name+':'+attr)
  if (ledger[name]['vertices'],ledger[name]['faces'])!=(ref['audit']['vertices'],ref['audit']['triangles']):
   raise ValueError('SOURCE_TOPOLOGY_MISMATCH:'+name)
 return {'authenticated_historical_manifest':True,'models_verified':94,'obj_hashes_verified':188,
   'individual_source_native_selfintersection_certified_here':False,
   'full_F_D_A_boolean_partition_certified_here':False}


def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--manifest')
 args=p.parse_args();ledger=regenerate(args.out)
 outcome={'schema':'w2-m18-original-source-parts-regeneration-v1',
   'source_scope':'RECONSTRUCTED_PHOTO_GUIDED_NOT_AUTHOR_CAD','parts_rebuilt':len(ledger),
   'model_and_si_files_rebuilt':len(ledger)*2,'source_corpus_digest':corpus_identity_sha(ledger),
   'all_188_historical_source_SHA_verified_against_frozen_main_manifest':True,'model_sha_ledger':ledger,
   'reference_manifest_authentication':'NOT_SUPPLIED',
   'native_boolean_calls':0,'cherchi_teacher_calls':0,'training_admitted':0}
 if args.manifest:outcome['full_manifest_audit']=validate_against_original_manifest(ledger,args.manifest)
 out=Path(args.out).parent/'M18_SOURCE_REGENERATION_RESULT.json'
 with out.open('x') as f:json.dump(outcome,f,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps({'parts_rebuilt':len(ledger),'manifest_verified':bool(args.manifest)}))
if __name__=='__main__':main()
