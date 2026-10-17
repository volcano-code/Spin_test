"""Independent full-area exact raw ten-moment integration before/after H4.

Contains no geometry modification, relies only on Python Fraction and stored H1/H4.
"""
from pathlib import Path
from fractions import Fraction
from hashlib import sha256
import json
import sys
from certify_h4_retriangulation import raw_ten_moments

def int_hash(value):
    n=abs(value);blob=n.to_bytes((n.bit_length()+7)//8,'big')
    return sha256((b'-' if value<0 else b'+')+blob).hexdigest()

def run(h1_path,h4_faces,output):
    h1_path,h4_faces,output=map(Path,(h1_path,h4_faces,output))
    mat=json.loads(h1_path.read_text());faces=json.loads(h4_faces.read_text())
    rational=[tuple(Fraction(x) for x in row) for row in mat['exact_vertices']]
    base=raw_ten_moments(mat['faces'],rational)
    changed=raw_ten_moments(faces,rational)
    diff=[x-y for x,y in zip(base,changed)]
    result={'schema':'heart-h4-independent-full-exact-ten-moments-v1',
        'base_sha256':sha256(h1_path.read_bytes()).hexdigest(),
        'candidate_faces_sha256':sha256(h4_faces.read_bytes()).hexdigest(),
        'moments_order':['volume','first_x','first_y','first_z','second_xx','second_yy','second_zz','second_yz','second_xz','second_xy'],
        'exact_zero_difference': all(x==0 for x in diff),
        'per_moment_equality':[x==y for x,y in zip(base,changed)],
        'original_moments_float':[float(x) for x in base],
        'candidate_moments_float':[float(x) for x in changed],
        'original_rational_num_sha256':[int_hash(x.numerator) for x in base],
        'original_rational_den_sha256':[int_hash(x.denominator) for x in base],
        'same_exact_rational_moments_sha256':[int_hash(x.numerator) for x in changed]==[int_hash(x.numerator) for x in base],
        'full_author_heart_verified':False}
    if not result['exact_zero_difference']:raise ValueError('EXACT_MOMENT_DIFFERENCE')
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({'exact_zero_difference':True,'count':len(base),'volume':float(base[0])}))
    return result
if __name__=='__main__':
    run(sys.argv[1],sys.argv[2],sys.argv[3])
