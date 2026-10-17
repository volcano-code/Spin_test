"""Lossless reconstruction of archived V4 *proxy* input, not original eval60."""
import argparse
import base64
import gzip
import hashlib
from pathlib import Path

SHA256='fa0a7eac8046be48fbfac495c7e6e283ebe7033d6242b64997aa28216b5c92f4'
ARCHIVE=Path(__file__).resolve().parents[1]/'input/archived-heart-v4-request.json.gz.b64'

def restore(path, archive=ARCHIVE):
    destination=Path(path)
    if destination.exists():raise ValueError('RESTORE_REQUIRES_FRESH_OUTPUT')
    payload=base64.b64decode(Path(archive).read_text().strip(),validate=True)
    raw=gzip.decompress(payload)
    if hashlib.sha256(raw).hexdigest()!=SHA256:
        raise ValueError('ARCHIVED_V4_INPUT_SHA256_MISMATCH')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(raw)
    return {'path':str(destination),'bytes':len(raw),'sha256':SHA256,
        'classification':'ARCHIVED_HEART_V4_PROXY_NOT_ORIGINAL_EVAL60'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args();print(restore(args.output))
if __name__=='__main__':main()
