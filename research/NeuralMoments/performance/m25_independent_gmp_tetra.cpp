// W1 M25 independent GMP signed-origin tetra integration; read-only; rho=1.
// This C++ helper never calls native Cherchi Boolean, production or Jacobian APIs.
// Input: n_vertices n_faces; N triples of exact rational text; F oriented triangles.
// Output: ten canonical hexadecimal num/den exact rational lines.
#include <gmpxx.h>
#include <array>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <limits>

using P = std::array<mpq_class,3>;
static const std::array<std::array<int,2>,6> PAIRS = {{{0,0},{1,1},{2,2},{1,2},{0,2},{0,1}}};
mpq_class parse(const std::string &s) {
    const auto pos=s.find('/');
    if (pos!=std::string::npos && s.find('/',pos+1)!=std::string::npos)
        throw std::runtime_error("BAD_FRACTION_SLASH");
    mpz_class a,b=1;
    if (mpz_set_str(a.get_mpz_t(),s.substr(0,pos).c_str(),0))
        throw std::runtime_error("BAD_NUMERATOR");
    if (pos!=std::string::npos &&
        (mpz_set_str(b.get_mpz_t(),s.substr(pos+1).c_str(),0) || b<=0))
        throw std::runtime_error("BAD_DENOMINATOR");
    mpq_class result(a,b);
    result.canonicalize();
    return result;
}
static std::string hex_rational(const mpq_class &q) {
    const mpz_class n=q.get_num(),d=q.get_den();
    const bool neg=n<0;
    mpz_class absn = neg ? mpz_class(-n) : n;
    std::string ns=absn.get_str(16);
    return std::string(neg?"-0x":"0x") + ns + "/0x"+d.get_str(16);
}
int main() {
    try {
        std::size_t n,f;
        if (!(std::cin>>n>>f) || n>300000 || f>600000) throw std::runtime_error("BAD_GEOMETRY_COUNTS");
        std::vector<P> vertices(n);
        std::string s;
        for (std::size_t i=0;i<n;++i)
            for (int k=0;k<3;++k){
                if (!(std::cin>>s) || s.size()>8192) throw std::runtime_error("BAD_VERTEX_TOKEN");
                vertices[i][k]=parse(s);
            }
        std::array<mpq_class,10> sum;
        for (std::size_t i=0;i<f;++i){
            std::size_t x,y,z;
            if (!(std::cin>>x>>y>>z) || x>=n || y>=n || z>=n || x==y || y==z || x==z)
                throw std::runtime_error("BAD_TRIANGLE");
            const P &a=vertices[x],&b=vertices[y],&c=vertices[z];
            // Signed-origin tetrahedron (0,a,b,c). Independent of Python implementation.
            const mpq_class det=a[0]*(b[1]*c[2]-b[2]*c[1])+
                                a[1]*(b[2]*c[0]-b[0]*c[2])+
                                a[2]*(b[0]*c[1]-b[1]*c[0]);
            const mpq_class vol=det/6;
            P t={a[0]+b[0]+c[0],a[1]+b[1]+c[1],a[2]+b[2]+c[2]};
            sum[0]+=vol;
            for(int k=0;k<3;++k) sum[1+k]+=vol*t[k]/4;
            for(int k=0;k<6;++k){
                int p=PAIRS[k][0],q=PAIRS[k][1];
                sum[4+k]+=vol*(t[p]*t[q]+a[p]*a[q]+b[p]*b[q]+c[p]*c[q])/20;
            }
        }
        for (const auto &x:sum) std::cout << hex_rational(x) << '\n';
        return 0;
    } catch(const std::exception &e){std::cerr << "FAIL_CLOSED:" << e.what()<<'\n';return 2;}
}
