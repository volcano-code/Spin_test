// W1 M28.2: exact cross-boundary intersection of saved Boolean output triangles
// against the opposite input operand. All narrow-phase predicates use GMP rationals.
// Input: out_nv out_nf other_nv other_nf; output exact vertices/faces; other exact vertices/faces.
#include <gmpxx.h>
#include <boost/geometry.hpp>
#include <boost/geometry/index/rtree.hpp>
#include <array>
#include <vector>
#include <string>
#include <iostream>
#include <stdexcept>
#include <algorithm>
#include <cmath>
#include <limits>
#include <chrono>
#include <cstdint>
#include <set>
namespace bg=boost::geometry; namespace bgi=boost::geometry::index;
using Q=mpq_class; using V=std::array<Q,3>; using V2=std::array<Q,2>; using I=std::array<int,3>;
using D=bg::model::point<double,3,bg::cs::cartesian>; using Box=bg::model::box<D>; using Elem=std::pair<Box,int>;
static Q parse(const std::string&s){auto p=s.find('/');if(p!=std::string::npos&&s.find('/',p+1)!=std::string::npos)throw std::runtime_error("INVALID_RATIONAL");mpz_class n,d=1;if(mpz_set_str(n.get_mpz_t(),s.substr(0,p).c_str(),0))throw std::runtime_error("INVALID_NUMERATOR");if(p!=std::string::npos&&(mpz_set_str(d.get_mpz_t(),s.substr(p+1).c_str(),0)||d<=0))throw std::runtime_error("INVALID_DENOMINATOR");Q q(n,d);q.canonicalize();return q;}
static V sub(const V&a,const V&b){return{a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
static V cross(const V&a,const V&b){return{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
static Q dot(const V&a,const V&b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static V interp(const V&a,const V&b,const Q&sa,const Q&sb){Q den=sa-sb;if(den==0)throw std::runtime_error("ZERO_INTERSECTION_DENOMINATOR");return{(sa*b[0]-sb*a[0])/den,(sa*b[1]-sb*a[1])/den,(sa*b[2]-sb*a[2])/den};}
static Q orient2(const V2&a,const V2&b,const V2&c){return(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);}
static V2 project(const V&p,int omit){return omit==0?V2{p[1],p[2]}:omit==1?V2{p[0],p[2]}:V2{p[0],p[1]};}
static bool point_in_tri(const V&p,const std::array<V,3>&t,const V&n){for(int i=0;i<3;++i)if(dot(cross(sub(t[(i+1)%3],t[i]),sub(p,t[i])),n)<0)return false;return true;}
static bool on_segment(const V&p,const V&a,const V&b){V d=sub(b,a),w=sub(p,a);V c=cross(d,w);if(c!=V{0,0,0})return false;Q t=dot(w,d),len=dot(d,d);return t>=0&&t<=len;}
static bool on_boundary(const V&p,const std::array<V,3>&t){return on_segment(p,t[0],t[1])||on_segment(p,t[1],t[2])||on_segment(p,t[2],t[0]);}
static void plane_hits(const std::array<V,3>&a,const V&na,const std::array<V,3>&b,std::vector<V>&hits){
 std::array<Q,3>s;for(int i=0;i<3;++i)s[i]=dot(na,sub(b[i],a[0]));
 for(int i=0;i<3;++i)if(s[i]==0&&point_in_tri(b[i],a,na))hits.push_back(b[i]);
 for(int i=0;i<3;++i){int j=(i+1)%3;if((s[i]<0&&s[j]>0)||(s[i]>0&&s[j]<0)){V p=interp(b[i],b[j],s[i],s[j]);if(point_in_tri(p,a,na))hits.push_back(std::move(p));}}
}
static Q cross2(const V2&a,const V2&b){return a[0]*b[1]-a[1]*b[0];}
static int classify_coplanar_intersection(const std::array<V,3>&out,const std::array<V,3>&other,const V&normal){
 int axis=0;for(int i=1;i<3;++i)if(abs(normal[i])>abs(normal[axis]))axis=i;
 V2 o0=project(other[0],axis),o1=project(other[1],axis),o2=project(other[2],axis);Q sign=orient2(o0,o1,o2);if(sign==0)throw std::runtime_error("DEGENERATE_OTHER_TRIANGLE_PROJECTION");
 std::vector<V>poly={out[0],out[1],out[2]};
 for(int e=0;e<3&&!poly.empty();++e){V2 u=project(other[e],axis),v=project(other[(e+1)%3],axis);auto prev=poly;poly.clear();
  for(size_t k=0;k<prev.size();++k){const V&c=prev[k],&d=prev[(k+1)%prev.size()];Q sc=orient2(u,v,project(c,axis))*sign,sd=orient2(u,v,project(d,axis))*sign;
   if((sc<0&&sd>0)||(sc>0&&sd<0))poly.push_back(interp(c,d,sc,sd));
   else if(sc<0&&sd==0)poly.push_back(d);
   if(sd>=0)poly.push_back(d);
  }
 }
 if(poly.empty())return 0;
 Q area=0;for(size_t i=0;i<poly.size();++i)area+=cross2(project(poly[i],axis),project(poly[(i+1)%poly.size()],axis));
 if(area!=0)return 2; // positive-area overlap necessarily enters output-triangle interior
 for(const V&p:poly)if(!on_boundary(p,out))return 2;
 // A zero-area clipped polygon can be a chord whose endpoints are both on the
 // output boundary. Its edge midpoints distinguish a legal boundary edge from
 // an illegal interior chord.
 for(size_t i=0;i<poly.size();++i){V mid;for(int k=0;k<3;++k)mid[k]=(poly[i][k]+poly[(i+1)%poly.size()][k])/2;if(!on_boundary(mid,out))return 2;}
 return 1;
}
static int classify_cross_boundary_intersection(const std::array<V,3>&out,const std::array<V,3>&other){
 V no=cross(sub(out[1],out[0]),sub(out[2],out[0]));V nb=cross(sub(other[1],other[0]),sub(other[2],other[0]));
 if(no==V{0,0,0}||nb==V{0,0,0})throw std::runtime_error("DEGENERATE_CROSS_BOUNDARY_TRIANGLE");
 std::array<Q,3>so,sb;for(int i=0;i<3;++i){so[i]=dot(nb,sub(out[i],other[0]));sb[i]=dot(no,sub(other[i],out[0]));}
 auto separated=[](const std::array<Q,3>&s){bool p=true,n=true;for(const auto&x:s){p&=x>0;n&=x<0;}return p||n;};
 if(separated(so)||separated(sb))return 0;
 if(so[0]==0&&so[1]==0&&so[2]==0&&sb[0]==0&&sb[1]==0&&sb[2]==0)
  return classify_coplanar_intersection(out,other,no);
 std::vector<V>hits;hits.reserve(12);plane_hits(out,no,other,hits);plane_hits(other,nb,out,hits);
 std::vector<V>unique;for(const auto&p:hits)if(std::find(unique.begin(),unique.end(),p)==unique.end())unique.push_back(p);
 if(unique.empty())return 0;
 for(const auto&p:unique)if(!on_boundary(p,out))return 2;
 if(unique.size()==1)return 1;
 size_t ia=0,ib=1;Q maxd=dot(sub(unique[0],unique[1]),sub(unique[0],unique[1]));
 for(size_t i=0;i<unique.size();++i)for(size_t j=i+1;j<unique.size();++j){V d=sub(unique[i],unique[j]);Q d2=dot(d,d);if(d2>maxd){maxd=d2;ia=i;ib=j;}}
 if(maxd==0)return 1;
 V mid;for(int k=0;k<3;++k)mid[k]=(unique[ia][k]+unique[ib][k])/2;
 return on_boundary(mid,out)?1:2;
}
static double bound(const Q&x,bool lower){double d=x.get_d();if(!std::isfinite(d))throw std::runtime_error("UNREPRESENTABLE_COORDINATE");for(int i=0;i<16;++i){Q q(d);if((lower&&q<=x)||(!lower&&q>=x))return d;d=std::nextafter(d,lower?-std::numeric_limits<double>::infinity():std::numeric_limits<double>::infinity());}throw std::runtime_error("OUTWARD_ROUNDING_FAILED");}
static Box box_for(const std::array<V,3>&t){double lo[3],hi[3];for(int k=0;k<3;++k){lo[k]=std::min({bound(t[0][k],true),bound(t[1][k],true),bound(t[2][k],true)});hi[k]=std::max({bound(t[0][k],false),bound(t[1][k],false),bound(t[2][k],false)});}return Box(D(lo[0],lo[1],lo[2]),D(hi[0],hi[1],hi[2]));}
int main(int argc,char**argv){auto start=std::chrono::steady_clock::now();try{
 int max_seconds=120;if(argc==3&&std::string(argv[1])=="--max-seconds")max_seconds=std::stoi(argv[2]);if(max_seconds<1||max_seconds>1800)throw std::runtime_error("INVALID_TIMEOUT");
 size_t on,of,bn,bf;if(!(std::cin>>on>>of>>bn>>bf)||on>300000||bn>300000||of>600000||bf>600000)throw std::runtime_error("INVALID_COUNTS");
 auto read_vertices=[](size_t n){std::vector<V>v(n);std::string s;for(auto&p:v)for(auto&x:p){if(!(std::cin>>s)||s.size()>200000)throw std::runtime_error("INVALID_VERTEX_TOKEN");x=parse(s);}return v;};
 auto read_faces=[](size_t n,size_t nv){std::vector<I>f(n);for(auto&t:f)for(auto&x:t)if(!(std::cin>>x)||x<0||static_cast<size_t>(x)>=nv)throw std::runtime_error("INVALID_FACE_INDEX");for(auto&t:f)if(t[0]==t[1]||t[1]==t[2]||t[0]==t[2])throw std::runtime_error("REPEATED_FACE_INDEX");return f;};
 auto ov=read_vertices(on);auto ofaces=read_faces(of,on);auto bv=read_vertices(bn);auto bfaces=read_faces(bf,bn);
 std::vector<std::array<V,3>> bt(bf);std::vector<V>bnorm(bf);using Tree=bgi::rtree<Elem,bgi::quadratic<16>>;Tree tree;
 for(size_t j=0;j<bf;++j){for(int k=0;k<3;++k)bt[j][k]=bv[bfaces[j][k]];bnorm[j]=cross(sub(bt[j][1],bt[j][0]),sub(bt[j][2],bt[j][0]));if(bnorm[j]==V{0,0,0})throw std::runtime_error("DEGENERATE_OTHER_INPUT_FACE");tree.insert({box_for(bt[j]),static_cast<int>(j)});}
 size_t candidates=0,exact=0,disjoint=0,boundary_contacts=0,interior=0;
 for(size_t i=0;i<of;++i){std::array<V,3>ot={ov[ofaces[i][0]],ov[ofaces[i][1]],ov[ofaces[i][2]]};V n=cross(sub(ot[1],ot[0]),sub(ot[2],ot[0]));if(n==V{0,0,0})throw std::runtime_error("DEGENERATE_OUTPUT_FACE");auto box=box_for(ot);std::vector<Elem>possible;tree.query(bgi::intersects(box),std::back_inserter(possible));candidates+=possible.size();
  for(const auto&e:possible){++exact;const int j=e.second;int classification=classify_cross_boundary_intersection(ot,bt[j]);if(classification==2){++interior;std::cout<<"status=OUTPUT_TRIANGLE_INTERSECTS_OPPOSITE_BOUNDARY_INTERIOR\noutput_face="<<i<<"\nother_face="<<j<<"\ncandidate_pairs="<<candidates<<"\nexact_pairs_checked="<<exact<<"\n";return 2;}else if(classification==1)++boundary_contacts;else ++disjoint;
   if((exact%512)==0&&std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()>max_seconds){std::cout<<"status=TIMEOUT_NO_CERTIFICATION\noutput_faces_completed="<<i<<"\nexact_pairs_checked="<<exact<<"\n";return 3;}
  }
 }
 std::cout<<"status=EXACT_NO_INTERIOR_CROSS_BOUNDARY_INTERSECTION\noutput_faces="<<of<<"\nother_faces="<<bf<<"\ncandidate_pairs="<<candidates<<"\nexact_pairs_checked="<<exact<<"\ndisjoint_candidate_pairs="<<disjoint<<"\nboundary_contact_pairs="<<boundary_contacts<<"\ninterior_cross_boundary_intersections="<<interior<<"\nelapsed_seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"\n";return 0;
 }catch(const std::exception&e){std::cout<<"status=INVALID_OR_UNVERIFIABLE\nreason="<<e.what()<<"\n";return 4;}}