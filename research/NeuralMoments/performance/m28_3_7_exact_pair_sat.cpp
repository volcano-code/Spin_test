#include <gmpxx.h>
#include <array>
#include <vector>
#include <string>
#include <iostream>
#include <algorithm>
#include <cmath>
#include <limits>
#include <chrono>
#include <set>
#include <cstdint>
using Z=mpz_class; using Q=mpq_class; using V=std::array<Z,3>; using I=std::array<int,3>;
using Box=std::array<double,6>;
static V sub(const V&a,const V&b){return{a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
static V cross(const V&a,const V&b){return{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
static Z dot(const V&a,const V&b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static bool separated(const V&axis,const std::array<V,3>&a,const std::array<V,3>&b){
 if(axis==V{0,0,0})return false;
 Z amin=dot(axis,a[0]),amax=amin,bmin=dot(axis,b[0]),bmax=bmin;
 for(int i=1;i<3;++i){Z x=dot(axis,a[i]),y=dot(axis,b[i]);if(x<amin)amin=x;if(x>amax)amax=x;if(y<bmin)bmin=y;if(y>bmax)bmax=y;}
 return amax<bmin||bmax<amin;
}
static bool tri_intersects_sat(const std::array<V,3>&a,const std::array<V,3>&b){
 V ea[3]={sub(a[1],a[0]),sub(a[2],a[1]),sub(a[0],a[2])};
 V eb[3]={sub(b[1],b[0]),sub(b[2],b[1]),sub(b[0],b[2])};
 V na=cross(ea[0],sub(a[2],a[0]));V nb=cross(eb[0],sub(b[2],b[0]));
 if(na==V{0,0,0}||nb==V{0,0,0})throw std::runtime_error("DEGENERATE_TRIANGLE");
 if(separated(na,a,b)||separated(nb,a,b))return false;
 for(int i=0;i<3;++i)for(int j=0;j<3;++j)if(separated(cross(ea[i],eb[j]),a,b))return false;
 // In-plane edge-normal axes make the test complete for coplanar triangles.
 for(int i=0;i<3;++i)if(separated(cross(na,ea[i]),a,b))return false;
 for(int i=0;i<3;++i)if(separated(cross(nb,eb[i]),a,b))return false;
 return true;
}
static bool box_overlap(const Box&a,const Box&b){
 for(int k=0;k<3;++k)if(a[k+3]<b[k]||b[k+3]<a[k])return false;
 return true;
}
static Box boxof(const std::array<V,3>&t,const std::array<std::array<double,3>,0>&dummy){
 (void)dummy;Box b;for(int k=0;k<3;++k){double lo=std::numeric_limits<double>::infinity(),hi=-lo;for(int i=0;i<3;++i){double x=t[i][k].get_d();lo=std::min(lo,x);hi=std::max(hi,x);}b[k]=lo;b[k+3]=hi;}return b;
}
using R=std::array<Q,3>; using R2=std::array<Q,2>;
static R rz(const V&p){return{Q(p[0]),Q(p[1]),Q(p[2])};}
static R rsub(const R&a,const R&b){return{a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
static R rcross(const R&a,const R&b){return{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
static Q rdot(const R&a,const R&b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static bool rinside(const R&p,const std::array<R,3>&t,const R&n){for(int i=0;i<3;++i)if(rdot(rcross(rsub(t[(i+1)%3],t[i]),rsub(p,t[i])),n)<0)return false;return true;}
static R rinterp(const R&a,const R&b,const Q&sa,const Q&sb){Q den=sa-sb;if(den==0)throw std::runtime_error("ZERO_RATIONAL_DENOM");return{(sa*b[0]-sb*a[0])/den,(sa*b[1]-sb*a[1])/den,(sa*b[2]-sb*a[2])/den};}
static void rhits(const std::array<R,3>&plane,const R&n,const std::array<R,3>&other,std::vector<R>&hits){
 std::array<Q,3>s;for(int i=0;i<3;++i)s[i]=rdot(n,rsub(other[i],plane[0]));
 for(int i=0;i<3;++i)if(s[i]==0&&rinside(other[i],plane,n))hits.push_back(other[i]);
 for(int i=0;i<3;++i){int j=(i+1)%3;if((s[i]<0&&s[j]>0)||(s[i]>0&&s[j]<0)){R p=rinterp(other[i],other[j],s[i],s[j]);if(rinside(p,plane,n))hits.push_back(p);}}
}
static R2 rproj(const R&p,int axis){return axis==0?R2{p[1],p[2]}:axis==1?R2{p[0],p[2]}:R2{p[0],p[1]};}
static Q rorient(const R2&a,const R2&b,const R2&c){return(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);}
static bool ronseg(const R2&p,const R2&a,const R2&b){if(rorient(a,b,p)!=0)return false;return p[0]>=std::min(a[0],b[0])&&p[0]<=std::max(a[0],b[0])&&p[1]>=std::min(a[1],b[1])&&p[1]<=std::max(a[1],b[1]);}
static std::set<R2> rseg_intersections(const R2&a,const R2&b,const R2&c,const R2&d){
 R2 r={b[0]-a[0],b[1]-a[1]},s={d[0]-c[0],d[1]-c[1]},q={c[0]-a[0],c[1]-a[1]};
 Q den=r[0]*s[1]-r[1]*s[0];
 if(den!=0){Q t=(q[0]*s[1]-q[1]*s[0])/den,u=(q[0]*r[1]-q[1]*r[0])/den;if(t>=0&&t<=1&&u>=0&&u<=1)return{{a[0]+t*r[0],a[1]+t*r[1]}};return{};}
 if(q[0]*r[1]-q[1]*r[0]!=0)return{};
 std::set<R2> out;for(const R2&p:{a,b,c,d})if(ronseg(p,a,b)&&ronseg(p,c,d))out.insert(p);return out;
}
static bool positive_dim_after_sat(const std::array<V,3>&az,const std::array<V,3>&bz){
 std::array<R,3>a={rz(az[0]),rz(az[1]),rz(az[2])},b={rz(bz[0]),rz(bz[1]),rz(bz[2])};
 R na=rcross(rsub(a[1],a[0]),rsub(a[2],a[0])),nb=rcross(rsub(b[1],b[0]),rsub(b[2],b[0]));
 std::array<Q,3>da,db;for(int i=0;i<3;++i){da[i]=rdot(nb,rsub(a[i],b[0]));db[i]=rdot(na,rsub(b[i],a[0]));}
 bool cop=(da[0]==0&&da[1]==0&&da[2]==0&&db[0]==0&&db[1]==0&&db[2]==0);
 if(cop){
  int axis=0;for(int i=1;i<3;++i)if(abs(na[i])>abs(na[axis]))axis=i;
  std::array<R2,3>ap,bp;for(int i=0;i<3;++i){ap[i]=rproj(a[i],axis);bp[i]=rproj(b[i],axis);}
  auto in2=[](const R2&p,const std::array<R2,3>&t){Q s0=rorient(t[0],t[1],p),s1=rorient(t[1],t[2],p),s2=rorient(t[2],t[0],p);return (s0>=0&&s1>=0&&s2>=0)||(s0<=0&&s1<=0&&s2<=0);};
  std::set<R2>p2;for(auto&p:ap)if(in2(p,bp))p2.insert(p);for(auto&p:bp)if(in2(p,ap))p2.insert(p);
  for(int i=0;i<3;++i)for(int j=0;j<3;++j){auto q=rseg_intersections(ap[i],ap[(i+1)%3],bp[j],bp[(j+1)%3]);p2.insert(q.begin(),q.end());}
  return p2.size()>=2;
 }
 std::vector<R>hits;rhits(a,na,b,hits);rhits(b,nb,a,hits);std::set<R>unique(hits.begin(),hits.end());return unique.size()>=2;
}
int main(){auto t0=std::chrono::steady_clock::now();try{
 size_t nvA,nfA,nvB,nfB;unsigned scale;if(!(std::cin>>nvA>>nfA>>nvB>>nfB>>scale))throw std::runtime_error("BAD_HEADER");
 auto readv=[](size_t n){std::vector<V>v(n);for(auto&p:v)for(auto&x:p)if(!(std::cin>>x))throw std::runtime_error("BAD_VERTEX");return v;};
 auto readf=[](size_t n,size_t nv){std::vector<I>f(n);for(auto&t:f)for(auto&x:t)if(!(std::cin>>x)||x<0||size_t(x)>=nv)throw std::runtime_error("BAD_FACE");return f;};
 auto va=readv(nvA);auto fa=readf(nfA,nvA);auto vb=readv(nvB);auto fb=readf(nfB,nvB);
 std::vector<std::array<V,3>>ta(nfA),tb(nfB);std::vector<Box>ba(nfA),bb(nfB);std::array<std::array<double,3>,0>dummy{};
 for(size_t i=0;i<nfA;++i){for(int k=0;k<3;++k)ta[i][k]=va[fa[i][k]];if(cross(sub(ta[i][1],ta[i][0]),sub(ta[i][2],ta[i][0]))==V{0,0,0})throw std::runtime_error("DEGENERATE_DESIGN_INPUT_FACE");ba[i]=boxof(ta[i],dummy);}
 for(size_t j=0;j<nfB;++j){for(int k=0;k<3;++k)tb[j][k]=vb[fb[j][k]];if(cross(sub(tb[j][1],tb[j][0]),sub(tb[j][2],tb[j][0]))==V{0,0,0})throw std::runtime_error("DEGENERATE_SOURCE_INPUT_FACE");bb[j]=boxof(tb[j],dummy);}
 size_t aabb=0,sat=0,positive=0;std::vector<std::pair<int,int>>pairs;
 for(size_t i=0;i<nfA;++i)for(size_t j=0;j<nfB;++j)if(box_overlap(ba[i],bb[j])){++aabb;if(tri_intersects_sat(ta[i],tb[j])){++sat;if(positive_dim_after_sat(ta[i],tb[j])){++positive;pairs.emplace_back(int(i),int(j));}}}
 std::cout<<"aabb_candidates "<<aabb<<"\nsat_contact_candidates "<<sat<<"\npositive_dim_cut_pairs "<<positive<<"\n";
 for(auto [i,j]:pairs)std::cout<<i<<" "<<j<<"\n";
 std::cout<<"elapsed_seconds "<<std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count()<<"\n";
 return 0;
 }catch(const std::exception&e){std::cerr<<"ERROR "<<e.what()<<"\n";return 2;}}
