"""Read-only, hash-authenticated collector for the user's original Heart run.

Run on the original research machine when the excluded output directory is
available. Never substitutes another run or older proxy geometry.
"""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile
from heart_h6_authority import verify_frozen_eval60,sha256


def collect(run_dir,registration,output):
    run_dir=Path(run_dir);registration=Path(registration);output=Path(output)
    paths={'configuration.json':run_dir/'configuration.json',
        'events.jsonl':run_dir/'events.jsonl',
        'registration.json':registration}
    status=verify_frozen_eval60(registration,paths['configuration.json'],paths['events.jsonl'])
    if output.exists():raise ValueError('EXCLUSIVE_OUTPUT_REQUIRED')
    output.parent.mkdir(parents=True,exist_ok=True)
    meta={'scope':'ORIGINAL_HEART_EVAL60_IDENTITY_PACK_ONLY_NOT_CONVERGED',
          'status':status,'files':{name:dict(bytes=p.stat().st_size,sha256=sha256(p)) for name,p in paths.items()}}
    try:
        with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,p in paths.items():archive.write(p,arcname=name)
            archive.writestr('identity.json',json.dumps(meta,indent=2)+'\n')
    except Exception:
        if output.exists():output.unlink()
        raise
    return meta


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',required=True,type=Path,help='original heart-certified-formal-seed-1-job-01/output/run')
    parser.add_argument('--registration',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(collect(args.run,args.registration,args.output),indent=2))
if __name__=='__main__':main()
