// W1 M26 independent exact post-Boolean surface self-intersection audit.
// Input format: n_vertices n_faces; 3 exact rational tokens per vertex; 3 unsigned indices per face.
// This is an offline audit; it does NOT certify material domains or Jacobians.
#include <gmpxx.h>
#include <boost/geometry.hpp>
#include <boost/geometry/index/rtree.hpp>
#include <array>
#include <vector>
#include <map>
#include <set>
#include <string>
#include <iostream>
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <chrono>
#include <cstdint>
namespace bg=boost::geometry;
namespace bgi=boost::geometry::index;
using Q=mpq_class;
using V=std::array<Q,3>;
using I=std::array<int,3>;
using D=bg::model::point<double,3,bg::cs::cartesian>;
using Box=bg::model::box<D>;
using Elem=std::pair<Box,int>;
using V2=std::array<Q,2>;

static Q parse(const std::string&s){
 auto p=s.find('/');if(p!=std::string::npos&&s.find('/',p+1)!=std::string::npos)throw std::runtime_error("INVALID_RATIONAL");
 mpz_class n,d=1;
 if(mpz_set_str(n.get_mpz_t(),s.substr(0,p).c_str(),0))throw std::runtime_error("INVALID_NUMERATOR");
 if(p!=std::string::npos&&(mpz_set_str(d.get_mpz_t(),s.substr(p+1).c_str(),0)||d<=0))throw std::runtime_error("INVALID_DENOMINATOR");
 Q q(n,d);q.canonicalize();return q;
}
static V sub(const V &a,const V&b){return{a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
static V cross(const V&a,const V&b){return{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
static Q dot(const V&a,const V&b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static V interpolate(const V&a,const V&b,const Q&sa,const Q&sb){
 const Q den=sa-sb;return{(sa*b[0]-sb*a[0])/den,(sa*b[1]-sb*a[1])/den,(sa*b[2]-sb*a[2])/den};
}
static bool point_in_tri(const V&x,const std::array<V,3>&t,const V&n){
 for(int i=0;i<3;++i){
   const V e=sub(t[(i+1)%3],t[i]);const V w=sub(x,t[i]);
   if(dot(cross(e,w),n)<0)return false;
 }
 return true;
}
static void plane_hits(const std::array<V,3>&a,const V&na,const std::array<V,3>&b,std::vector<V>&hits){
 std::array<Q,3>s;
 for(int i=0;i<3;++i)s[i]=dot(na,sub(b[i],a[0]));
 for(int i=0;i<3;++i) if(s[i]==0&&point_in_tri(b[i],a,na))hits.push_back(b[i]);
 for(int i=0;i<3;++i){int j=(i+1)%3;
   if((s[i]<0&&s[j]>0)||(s[i]>0&&s[j]<0)){
       V p=interpolate(b[i],b[j],s[i],s[j]);
       if(point_in_tri(p,a,na))hits.push_back(std::move(p));
   }
 }
}
static Q cross2(const V2&a,const V2&b){return a[0]*b[1]-a[1]*b[0];}
static Q orient2(const V2&a,const V2&b,const V2&c){return cross2({b[0]-a[0],b[1]-a[1]},{c[0]-a[0],c[1]-a[1]});}
static V2 project(const V&v,int omit){return omit==0?V2{v[1],v[2]}:omit==1?V2{v[0],v[2]}:V2{v[0],v[1]};}
static bool on_allowed_feature(const V&p,const std::array<int,3>&fa,const std::array<int,3>&fb,const std::vector<V>&vertices){
 std::vector<int>shared;for(int x:fa)for(int y:fb)if(x==y)shared.push_back(x);
 if(shared.empty())return false;
 if(shared.size()==1)return p==vertices[shared[0]];
 if(shared.size()==2){
  const V&a=vertices[shared[0]],&b=vertices[shared[1]];
  V w=sub(b,a),u=sub(p,a);V z=cross(w,u);
  if(z[0]!=0||z[1]!=0||z[2]!=0)return false;
  Q s=dot(u,w),m=dot(w,w);return s>=0&&s<=m;
 }
 return false; // identical faces or non-manifold faces are not admissible
}
// Clipped polygon carries full 3D points, projected just for planar orientation.
static bool coplanar_illegal(const std::array<V,3>&a,const std::array<V,3>&b,const V&na,
                            const I&fa,const I&fb,const std::vector<V>&vertices){
 int axis=0;for(int i=1;i<3;++i)if(abs(na[i])>abs(na[axis]))axis=i;
 const V2 bp0=project(b[0],axis),bp1=project(b[1],axis),bp2=project(b[2],axis);
 const Q sign=orient2(bp0,bp1,bp2);
 if(sign==0)throw std::runtime_error("COPLANAR_PROJECT_DEGENERATE");
 std::vector<V>poly={a[0],a[1],a[2]};
 for(int e=0;e<3&&(!poly.empty());++e){
   const V2 u=project(b[e],axis),v=project(b[(e+1)%3],axis);
   const std::vector<V>prev=poly;poly.clear();
   for(size_t k=0;k<prev.size();++k){
     const V&c=prev[k],&d=prev[(k+1)%prev.size()];
     const Q sc=orient2(u,v,project(c,axis))*sign,sd=orient2(u,v,project(d,axis))*sign;
     if((sc<0&&sd>0)||(sc>0&&sd<0)) poly.push_back(interpolate(c,d,sc,sd));
     else if(sc<0&&sd==0)poly.push_back(d);
     if(sd>=0)poly.push_back(d);
   }
 }
 if(poly.empty())return false;
 // Nonzero intersection area means intersecting interiors (including coplanar adjacent overlap).
 Q area2=0;for(size_t i=0;i<poly.size();++i)
    area2+=cross2(project(poly[i],axis),project(poly[(i+1)%poly.size()],axis));
 if(area2!=0)return true;
 for(auto&p:poly)if(!on_allowed_feature(p,fa,fb,vertices))return true;
 return false;
}
static bool illegal_intersection(const std::array<V,3>&a,const std::array<V,3>&b,const V&na,const V&nb,
                                 const I&fa,const I&fb,const std::vector<V>&vertices){
 std::array<Q,3>sa,sb;
 for(int i=0;i<3;++i){sa[i]=dot(nb,sub(a[i],b[0]));sb[i]=dot(na,sub(b[i],a[0]));}
 const auto separated=[](const std::array<Q,3>&s){
  bool all_plus=true,all_minus=true;
  for(auto&x:s){all_plus&=(x>0);all_minus&=(x<0);}return all_plus||all_minus;
 };
 if(separated(sa)||separated(sb))return false;
 if(sa[0]==0&&sa[1]==0&&sa[2]==0&&sb[0]==0&&sb[1]==0&&sb[2]==0)
   return coplanar_illegal(a,b,na,fa,fb,vertices);
 std::vector<V>hits;hits.reserve(12);
 plane_hits(a,na,b,hits);plane_hits(b,nb,a,hits);
 for(const auto&p:hits)if(!on_allowed_feature(p,fa,fb,vertices))return true;
 return false;
}
static double bound(const Q&x,bool lower){
 double d=x.get_d();if(!std::isfinite(d))throw std::runtime_error("UNREPRESENTABLE_COORDINATE");
 // Compare EXACT rational value of binary64 to exact GMP coordinate; move outward.
 for(int i=0;i<16;++i){
    Q q(d);if((lower&&q<=x)||(!lower&&q>=x))return d;
    d=std::nextafter(d,lower?-std::numeric_limits<double>::infinity():std::numeric_limits<double>::infinity());
 }
 throw std::runtime_error("OUTWARD_ROUNDING_FAILED");
}
int main(int argc,char**argv){
 auto start=std::chrono::steady_clock::now();
 try{
  int max_seconds=120;
  if(argc==3&&std::string(argv[1])=="--max-seconds")max_seconds=std::stoi(argv[2]);
  if(max_seconds<1||max_seconds>1800)throw std::runtime_error("INVALID_TIMEOUT");
  size_t n,f;if(!(std::cin>>n>>f)||n>300000||f>600000)throw std::runtime_error("INVALID_COUNTS");
  std::vector<V>vs(n);std::string s;
  for(auto &v:vs)for(auto &x:v){if(!(std::cin>>s)||s.size()>200000)throw std::runtime_error("INVALID_VERTEX");x=parse(s);}
  std::vector<I>fs(f);std::vector<V>normals(f);
  std::map<std::pair<int,int>,std::pair<int,int>>edges;
  std::map<std::pair<int,int>,std::vector<int>>edge_faces;
  std::vector<std::vector<int>> incident(n);
  for(size_t j=0;j<f;++j){
   I &face=fs[j];for(auto &idx:face){if(!(std::cin>>idx)||idx<0||idx>=(int)n)throw std::runtime_error("BAD_FACE_INDEX");}
   if(face[0]==face[1]||face[0]==face[2]||face[1]==face[2])throw std::runtime_error("REPEATED_VERTEX");
   normals[j]=cross(sub(vs[face[1]],vs[face[0]]),sub(vs[face[2]],vs[face[0]]));
   if(normals[j]==V{0,0,0})throw std::runtime_error("DEGENERATE_EXACT_TRIANGLE");
   for(int k=0;k<3;++k){int a=face[k],b=face[(k+1)%3];
    incident[a].push_back((int)j);
    auto key=std::make_pair(std::min(a,b),std::max(a,b));
    auto &e=edges[key]; e.first++;e.second+=(a<b?1:-1); edge_faces[key].push_back((int)j);}
  }
  if(f==0){if(n)throw std::runtime_error("ORPHAN_VERTICES_IN_EMPTY_MATERIAL");
    std::cout<<"status=STRICT_EMPTY_NO_POSITIVE_MASS\n";return 0;}
  for(const auto&e:edges)if(e.second.first!=2||e.second.second!=0)
    throw std::runtime_error("NOT_CLOSED_ORIENTED_TWO_MANIFOLD_EDGE");
  // A closed edge manifold can still pinch two disconnected face fans at a vertex.
  // Require exactly one connected link per vertex (and no orphan vertex).
  for(size_t v=0;v<n;++v){
    if(incident[v].empty())throw std::runtime_error("UNREFERENCED_VERTEX");
    std::set<int> seen;std::vector<int> todo{incident[v][0]};
    while(!todo.empty()){
      int fi=todo.back();todo.pop_back();
      if(!seen.insert(fi).second)continue;
      const I &face=fs[fi];
      for(int k=0;k<3;++k){
        int a=face[k],b=face[(k+1)%3];
        if(a!=(int)v && b!=(int)v)continue;
        auto it=edge_faces.find({std::min(a,b),std::max(a,b)});
        if(it==edge_faces.end()||it->second.size()!=2)
          throw std::runtime_error("NONMANIFOLD_VERTEX_LINK");
        for(int other:it->second)if(!seen.count(other))todo.push_back(other);
      }
    }
    if(seen.size()!=incident[v].size())throw std::runtime_error("NONMANIFOLD_VERTEX_LINK");
  }
  typedef bgi::rtree<Elem,bgi::quadratic<16>> Tree;
  Tree rtree;
  size_t candidate=0,exact_tested=0,adjacent=0,nonadjacent=0;
  for(size_t i=0;i<f;++i){
   const auto &face=fs[i];
   double lo[3],hi[3];
   for(int k=0;k<3;++k){
     lo[k]=std::min({bound(vs[face[0]][k],true),bound(vs[face[1]][k],true),bound(vs[face[2]][k],true)});
     hi[k]=std::max({bound(vs[face[0]][k],false),bound(vs[face[1]][k],false),bound(vs[face[2]][k],false)});
   }
   Box box(D(lo[0],lo[1],lo[2]),D(hi[0],hi[1],hi[2]));
   std::vector<Elem>possible;rtree.query(bgi::intersects(box),std::back_inserter(possible));
   candidate+=possible.size();
   std::array<V,3>a={vs[face[0]],vs[face[1]],vs[face[2]]};
   for(const auto&el:possible){
    int j=el.second;const auto&other=fs[j];
    int shared=0;for(auto x:face)for(auto y:other)if(x==y)shared++;
    if(shared)adjacent++;else nonadjacent++;
    std::array<V,3>b={vs[other[0]],vs[other[1]],vs[other[2]]};
    exact_tested++;
    if(illegal_intersection(a,b,normals[i],normals[j],face,other,vs)){
      std::cout<<"status=POST_BOOLEAN_SELF_INTERSECTION\n"<<"face_a="<<j<<"\nface_b="<<i<<"\n"
               <<"candidate_pairs="<<candidate<<"\nexact_pairs_checked="<<exact_tested<<"\n";
      return 2;
    }
    if((exact_tested%256)==0&&std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()>max_seconds){
      std::cout<<"status=TIMEOUT_NO_CERTIFICATION\n"<<"exact_pairs_checked="<<exact_tested<<"\n";
      return 3;
    }
   }
   rtree.insert(std::make_pair(box,(int)i));
  }
  std::cout<<"status=EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE\n"
           <<"vertices="<<n<<"\nfaces="<<f<<"\n"
           <<"candidate_pairs="<<candidate<<"\nexact_pairs_checked="<<exact_tested<<"\n"
           <<"adjacent_pairs="<<adjacent<<"\nnonadjacent_pairs="<<nonadjacent<<"\n"
           <<"elapsed_seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"\n";
  return 0;
 }catch(const std::exception&e){
  std::cout<<"status=INVALID_OR_UNVERIFIABLE\nreason="<<e.what()<<"\n";return 4;
 }
}
