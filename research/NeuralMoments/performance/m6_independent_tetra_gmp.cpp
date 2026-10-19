// W1 M6: independent exact tetrahedral GMP integration of archived Cherchi materials.
// NOT production _cherchi_rational_moments (which uses surface divergence),
// NOT a Boolean, exact self-intersection audit, or a Newton computation.
// Input is exclusively W1_REAL_H8_V1 followed by vertex and face rows.
#include <gmpxx.h>
#include <array>
#include <chrono>
#include <cstddef>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

using Q = mpq_class;
using V = std::array<Q,3>;
using F = std::array<std::size_t,3>;
using Ten = std::array<Q,10>;
using Clock = std::chrono::steady_clock;
static constexpr std::array<std::array<int,2>,6> pairs{{{0,0},{1,1},{2,2},{1,2},{0,2},{0,1}}};
static long long ns(Clock::time_point start) {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count();
}
Q token(const std::string &s) {
    if (s.size() > 2048 || s.empty()) throw std::invalid_argument("INVALID_EXACT_TOKEN_LENGTH");
    auto slash = s.find('/');
    if (slash==std::string::npos || slash==0 || slash+1==s.size() || s.find('/',slash+1)!=std::string::npos)
        throw std::invalid_argument("INVALID_EXACT_RATIONAL_TOKEN");
    for (std::size_t i=0;i<s.size();++i) {
        if (i==slash || (i==0 && s[i]=='-')) continue;
        if (s[i]<'0' || s[i]>'9') throw std::invalid_argument("RATIONAL_NONDECIMAL_CHARACTER");
    }
    Q v(s);
    if (v.get_den()<=0) throw std::invalid_argument("NONPOSITIVE_DENOMINATOR");
    v.canonicalize();
    if (v.get_num().get_str()+"/"+v.get_den().get_str()!=s)
        throw std::invalid_argument("NONCANONICAL_EXACT_RATIONAL");
    return v;
}

struct Geometry { std::vector<V> points; std::vector<F> faces; };
Geometry read_input(std::istream &in) {
    std::string magic; if (!(in>>magic) || magic!="W1_REAL_H8_V1")
        throw std::invalid_argument("ARCHIVED_STREAM_MAGIC_MISMATCH");
    long long nv=-1,nf=-1;
    if (!(in>>nv>>nf) || nv<4 || nv>100000 || nf<4 || nf>200000)
        throw std::invalid_argument("ARCHIVED_STREAM_SIZE_INVALID");
    Geometry g;
    g.points.reserve(static_cast<std::size_t>(nv));
    for(long long i=0;i<nv;++i){
        V p;
        for(int j=0;j<3;++j){std::string s;if(!(in>>s))throw std::invalid_argument("TRUNCATED_VERTEX_ROW");p[j]=token(s);}
        g.points.push_back(std::move(p));
    }
    g.faces.reserve(static_cast<std::size_t>(nf));
    for(long long i=0;i<nf;++i){
        long long a=-1,b=-1,c=-1;
        if (!(in>>a>>b>>c)) throw std::invalid_argument("TRUNCATED_FACE_ROW");
        if (a<0||b<0||c<0||a>=nv||b>=nv||c>=nv||a==b||b==c||a==c)
            throw std::invalid_argument("INVALID_FACE_INDEX");
        g.faces.push_back({static_cast<std::size_t>(a),static_cast<std::size_t>(b),static_cast<std::size_t>(c)});
    }
    std::string extra;
    if (in>>extra) throw std::invalid_argument("TRAILING_STREAM_DATA");
    return g;
}
void boundary_gate(const Geometry &g) {
    std::map<std::pair<std::size_t,std::size_t>,std::pair<int,int>> edges;
    for (const F &f : g.faces) {
        const V &a=g.points[f[0]],&b=g.points[f[1]],&c=g.points[f[2]];
        V u,v;
        for(int i=0;i<3;++i){u[i]=b[i]-a[i];v[i]=c[i]-a[i];}
        const Q x=u[1]*v[2]-u[2]*v[1],y=u[2]*v[0]-u[0]*v[2],z=u[0]*v[1]-u[1]*v[0];
        if (x==0 && y==0 && z==0) throw std::invalid_argument("EXACT_ZERO_AREA_FACE");
        for(int j=0;j<3;++j){
            const std::size_t a=f[j],b=f[(j+1)%3];
            auto &rec=edges[{std::min(a,b),std::max(a,b)}];
            rec.first++;
            rec.second+=a<b?1:-1;
        }
    }
    for (const auto &e : edges)
        if(e.second.first!=2 || e.second.second!=0)
            throw std::invalid_argument("OPEN_OR_MISORIENTED_EXACT_BOUNDARY");
}
// Exact balanced summation: identical rational result to sequential addition.
struct RationalSum {
    std::vector<std::optional<Q>> bins;
    void add(Q value) {
        std::size_t i=0;
        while(i<bins.size() && bins[i]){value+=*bins[i];bins[i].reset();++i;}
        if(i==bins.size())bins.emplace_back(std::move(value));
        else bins[i]=std::move(value);
    }
    Q total() const {Q out=0;for(const auto &v:bins)if(v)out+=*v;return out;}
};
Ten exact_tetra(const Geometry &g) {
    std::array<RationalSum,10> sums;
    // Independent tetrahedron-at-world-origin integral. This does NOT use
    // the production surface divergence area*constant identities.
    for(const F &f:g.faces){
        const V &a=g.points[f[0]],&b=g.points[f[1]],&c=g.points[f[2]];
        const Q det=a[0]*(b[1]*c[2]-b[2]*c[1])
                   +a[1]*(b[2]*c[0]-b[0]*c[2])
                   +a[2]*(b[0]*c[1]-b[1]*c[0]);
        if(det==0)continue; // degenerate *origin tetrahedron*, not face.
        sums[0].add(det/6);
        V s;
        for(int i=0;i<3;++i){s[i]=a[i]+b[i]+c[i];sums[i+1].add(det*s[i]/24);}
        for(int j=0;j<6;++j){
            const int x=pairs[j][0],y=pairs[j][1];
            sums[j+4].add(det*(s[x]*s[y]+a[x]*a[y]+b[x]*b[y]+c[x]*c[y])/120);
        }
    }
    Ten out;
    for(int i=0;i<10;++i)out[i]=sums[i].total();
    if(out[0]<=0)throw std::invalid_argument("NONPOSITIVE_EXACT_MASS");
    return out;
}
int main(int argc,char **) {
    try {
        if (argc!=1)throw std::invalid_argument("NO_OPTIONAL_BYPASS_FLAGS");
        const auto start=Clock::now();
        Geometry g=read_input(std::cin);
        const long long parse_ns=ns(start);
        const auto gstart=Clock::now();boundary_gate(g);
        const long long gate_ns=ns(gstart);
        const auto tstart=Clock::now();Ten moments=exact_tetra(g);
        const long long tetra_ns=ns(tstart);
        std::cout<<"{\"schema\":\"w1-m6-exact-independent-tetra-v1\","
                 <<"\"scope\":\"ARCHIVED_H8_EXACT_TETRA_INDEPENDENT_OF_PRODUCTION_SURFACE\","
                 <<"\"vertices\":"<<g.points.size()<<",\"faces\":"<<g.faces.size()<<","
                 <<"\"input_parse_ns\":"<<parse_ns<<",\"full_boundary_gate_ns\":"<<gate_ns
                 <<",\"independent_tetra_ns\":"<<tetra_ns
                 <<",\"exact_ten\":[";
        for(int i=0;i<10;++i){if(i)std::cout<<',';std::cout<<'"'<<moments[i].get_num().get_str()<<'/'<<moments[i].get_den().get_str()<<'"';}
        std::cout<<"],\"fresh_boolean\":false,\"new_self_intersection_audit\":false,"
                 <<"\"full_solver_speedup\":null,\"paper_speed_qualified\":false}\n";
        return 0;
    } catch(const std::exception &e){std::cerr<<"W1_M6_FAILED:"<<e.what()<<'\n';return 2;}
}
