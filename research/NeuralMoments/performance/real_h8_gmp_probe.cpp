// W1 M3: archived REAL H8 rational Cherchi material, isolated GMP ownership trial.
// Not a new Cherchi Boolean run, independent self-intersection audit, nor production ABI.
#include <gmpxx.h>
#include <array>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>
#include <sstream>
using Rational=mpq_class;
using Point=std::array<Rational,3>;
using Face=std::array<size_t,3>;
using Clock=std::chrono::steady_clock;
struct Geometry {std::vector<Point> vertices;std::vector<Face> faces;};
using Ten=std::array<Rational,10>;
static uint64_t now_ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count();}
static Rational parse(const std::string& token){
 auto slash=token.find('/');
 if(slash!=std::string::npos && token.find('/',slash+1)!=std::string::npos)throw std::invalid_argument("BAD_RATIONAL_TOKEN");
 auto a=token.substr(0,slash),b=(slash==std::string::npos ? "1" : token.substr(slash+1));
 mpz_class num,den;
 if(a.empty()||b.empty()||mpz_set_str(num.get_mpz_t(),a.c_str(),0)!=0||mpz_set_str(den.get_mpz_t(),b.c_str(),0)!=0||den<=0)throw std::invalid_argument("BAD_RATIONAL_NUMBER");
 Rational r(num,den);r.canonicalize();return r;
}
static Geometry load(std::istream& in){
 std::string magic;in>>magic;
 if(magic!="W1_REAL_H8_V1")throw std::invalid_argument("BAD_STREAM_MAGIC");
 size_t n,m; if(!(in>>n>>m)||n<4||m<4||n>100000||m>200000)throw std::invalid_argument("INVALID_MATERIAL_DIMS");
 Geometry g;g.vertices.reserve(n);g.faces.reserve(m);
 for(size_t i=0;i<n;++i){std::string a,b,c;if(!(in>>a>>b>>c))throw std::invalid_argument("TRUNCATED_EXACT_VERTICES");g.vertices.push_back({parse(a),parse(b),parse(c)});}
 for(size_t i=0;i<m;++i){long long a,b,c;if(!(in>>a>>b>>c)||a<0||b<0||c<0||static_cast<size_t>(a)>=n||static_cast<size_t>(b)>=n||static_cast<size_t>(c)>=n)throw std::invalid_argument("INVALID_FACE_INDEX");g.faces.push_back({static_cast<size_t>(a),static_cast<size_t>(b),static_cast<size_t>(c)});}
 std::string extra;if(in>>extra)throw std::invalid_argument("EXTRA_STREAM_BYTES");return g;
}
static std::array<Rational,3> area(const Point& a,const Point& b,const Point& c){
 const auto ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2];
 const auto vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2];
 return {Rational(uy*vz-uz*vy),Rational(uz*vx-ux*vz),Rational(ux*vy-uy*vx)};
}
static void boundary_gate(const Geometry&g){
 if(g.vertices.size()<4||g.faces.size()<4)throw std::invalid_argument("BAD_MATERIAL_SIZE");
 std::map<std::pair<size_t,size_t>,std::pair<int,int>> edges;
 for(const Face &f:g.faces){
  if(f[0]>=g.vertices.size()||f[1]>=g.vertices.size()||f[2]>=g.vertices.size())throw std::invalid_argument("FACE_OUT_OF_BOUNDS");
  if(f[0]==f[1]||f[1]==f[2]||f[2]==f[0])throw std::invalid_argument("REPEATED_FACE_VERTEX");
  auto a=area(g.vertices[f[0]],g.vertices[f[1]],g.vertices[f[2]]);
  if(a[0]==0&&a[1]==0&&a[2]==0)throw std::invalid_argument("EXACT_ZERO_AREA");
  for(int j=0;j<3;++j){const auto u=f[j],v=f[(j+1)%3];auto& t=edges[{std::min(u,v),std::max(u,v)}];++t.first;t.second+=(u<v?1:-1);}
 }
 for(auto& entry:edges)if(entry.second.first!=2||entry.second.second!=0)throw std::invalid_argument("OPEN_NONMANIFOLD_OR_MISORIENTED");
}
struct ExactSum {std::vector<std::optional<Rational>> partials;
 void add(Rational v){size_t i=0;while(i<partials.size()&&partials[i]){v+=*partials[i];partials[i].reset();++i;}if(i==partials.size())partials.emplace_back(std::move(v));else partials[i]=std::move(v);}
 Rational total()const{Rational v=0;for(const auto&p:partials)if(p)v+=*p;return v;}
};
static Ten integrate(const Geometry& g){
 constexpr std::array<std::array<int,2>,6> pairs{{{0,0},{1,1},{2,2},{1,2},{0,2},{0,1}}};
 std::array<ExactSum,10> sums;
 for(const Face& f:g.faces){
  const auto ar=area(g.vertices[f[0]],g.vertices[f[1]],g.vertices[f[2]]);
  Point first{};std::array<Rational,6> second{};
  for(auto idx:f){const Point&v=g.vertices[idx];for(int k=0;k<3;k++)first[k]+=v[k];for(int k=0;k<6;k++)second[k]+=v[pairs[k][0]]*v[pairs[k][1]];}
  Rational c=0;for(int k=0;k<3;k++)c+=ar[k]*g.vertices[f[0]][k];
  sums[0].add(c/6);
  for(int k=0;k<3;k++)sums[k+1].add(c*first[k]/24);
  for(int k=0;k<6;k++){auto p=pairs[k][0],q=pairs[k][1];sums[k+4].add(c*(first[p]*first[q]+second[k])/120);}
 }
 Ten out{};for(int k=0;k<10;k++)out[k]=sums[k].total();
 if(out[0]<=0)throw std::invalid_argument("NONPOSITIVE_MASS");
 return out;
}
static std::shared_ptr<const Geometry> prepared(const std::shared_ptr<const Geometry>& source){
 if(!source)throw std::invalid_argument("NULL_SOURCE_REF");
 return source;
}
static Geometry roundtrip(const Geometry& g){
 Geometry copy;copy.faces=g.faces;copy.vertices.reserve(g.vertices.size());
 for(const auto& row:g.vertices)copy.vertices.push_back({parse(row[0].get_str()),parse(row[1].get_str()),parse(row[2].get_str())});
 return copy;
}
int main(int argc,char**argv){
 try{
  if(argc!=3||std::string(argv[1])!="--real-h8")
    throw std::invalid_argument("USAGE: --real-h8 REPEATS < packet.stream");
  const std::string amount=argv[2];
  if(amount.size()!=1||amount[0]<'1'||amount[0]>'8')throw std::invalid_argument("REPEATS_OUT_OF_RANGE");
  const int repeats=amount[0]-'0';
  const auto begin=now_ns();auto source=std::make_shared<Geometry>(load(std::cin));
  const auto parsed=now_ns();
  Ten reference{};bool have_reference=false;
  struct Stage {std::string variant;int round;uint64_t ref_ns,gate_ns,gmp_ns,total_ns;};
  std::vector<Stage> timings;timings.reserve(2*repeats);
  for(int r=0;r<repeats;r++){
   for(int k=0;k<2;k++){
    const bool prepared_first = r%2==1;
    const bool is_prepared = (k==0)==prepared_first;
    const auto t0=now_ns();
    Ten value;
    uint64_t t1=0,t2=0;
    if(is_prepared){
     const auto held=prepared(source);t1=now_ns();
     boundary_gate(*held);t2=now_ns();
     value=integrate(*held);
    }else{
     Geometry copy=roundtrip(*source);t1=now_ns();
     boundary_gate(copy);t2=now_ns();
     value=integrate(copy);
    }
    const auto t3=now_ns();
    if(have_reference){for(int i=0;i<10;i++)if(value[i]!=reference[i])
      throw std::runtime_error("EXACT_TEN_NOT_EQUAL");}
    else{reference=std::move(value);have_reference=true;}
    timings.push_back({is_prepared?"prepared":"legacy",r,t1-t0,t2-t1,t3-t2,t3-t0});
   }
  }
  const auto finish=now_ns();
  std::cout<<"{\"schema\":\"w1-m3-real-h8-exact-gmp-v2\",\"scope\":\"ARCHIVED_REAL_CHERCHI_PACKET_GMP_ONLY_NOT_SOLVER\",\"vertices\":"<<source->vertices.size()
    <<",\"faces\":"<<source->faces.size()<<",\"input_parse_ns\":"<<parsed-begin
    <<",\"process_wall_ns\":"<<finish-begin<<",\"repeats\":"<<repeats
    <<",\"order\":\"AB_BA_ALTERNATION\",\"exact_ten_moments_equal\":true,\"topology_admitted_each_iteration\":true,\"independent_self_intersection_rechecked\":false,\"recomputed_cherchi_boolean\":false,\"jacobian_recomputed\":false,\"full_solver_measured\":false,\"stages\":[";
  for(size_t i=0;i<timings.size();++i){const auto &t=timings[i];if(i)std::cout<<',';
   std::cout<<"{\"variant\":\""<<t.variant<<"\",\"round\":"<<t.round<<",\"reference_or_roundtrip_ns\":"<<t.ref_ns<<",\"boundary_gate_ns\":"<<t.gate_ns<<",\"gmp_ten_ns\":"<<t.gmp_ns<<",\"total_ns\":"<<t.total_ns<<"}";}
  std::cout<<"],\"ten_exact\":[";
  for(int i=0;i<10;i++){if(i)std::cout<<',';std::cout<<'"'<<reference[i].get_str()<<'"';}
  std::cout<<"]}\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<"W1_M3_REJECTED:"<<e.what()<<"\n";return 2;}
}
