"""Run one source+Cherchi binary evaluation on an explicit proxy input.
No CGAL Boolean invocation and no hidden fallback. Strict status only.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from cherchi_heart_guard import load_modules,evaluate_proxy,publish,digest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fixture',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    fixture=json.loads(args.fixture.read_text())
    native,cherchi=load_modules()
    packet,report=evaluate_proxy(native,cherchi,fixture)
    report=publish(args.output,packet,report)
    report['native_module_sha256']=digest(Path(native.__file__))
    report['cherchi_module_sha256']=digest(Path(cherchi.__file__))
    report['fixture_sha256']=digest(args.fixture)
    (args.output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report,allow_nan=False))
    if not report['binary64_boundary_passed']:
        print('FLOAT_EXPORT_BLOCKED: rational evidence retained, no OBJ created.',file=sys.stderr)

if __name__=='__main__':main()
