// W1 M2: isolated exact-GMP ownership/roundtrip experiment, NOT production ABI.
// Both branches check every oriented edge and exact zero-area face before integrating.
#include <gmpxx.h>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using Rational = mpq_class;
using Point = std::array<Rational, 3>;
using Face = std::array<std::size_t, 3>;
using Moments = std::array<Rational, 10>;
using Clock = std::chrono::steady_clock;

struct Geometry {
    std::vector<Point> points;
    std::vector<Face> faces;
};

Point area_vector(const Point& a, const Point& b, const Point& c) {
    Point u, v;
    for (int k = 0; k != 3; ++k) { u[k] = b[k] - a[k]; v[k] = c[k] - a[k]; }
    return {u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]};
}

// Arithmetic-only boundary admission: closed, consistently oriented,
// nondegenerate triangles. NOT a substitute for native self-intersection audit.
void check_boundary(const Geometry& g) {
    if (g.points.size() < 4 || g.faces.size() < 4) throw std::runtime_error("BAD_GEOMETRY_SIZE");
    std::map<std::pair<std::size_t,std::size_t>,std::pair<int,int>> edges;
    for (const Point& v : g.points) for (const Rational& coordinate : v) {
        Rational canonical=coordinate; canonical.canonicalize();
        if (canonical.get_num()!=coordinate.get_num() ||
            canonical.get_den()!=coordinate.get_den())
            throw std::runtime_error("NONCANONICAL_SOURCE_RATIONAL");
    }
    for (const Face& f : g.faces) {
        for (std::size_t v : f) if (v >= g.points.size()) throw std::runtime_error("FACE_OUT_OF_BOUNDS");
        if (f[0] == f[1] || f[1] == f[2] || f[2] == f[0]) throw std::runtime_error("REPEATED_INDEX");
        Point area = area_vector(g.points[f[0]],g.points[f[1]],g.points[f[2]]);
        if (area[0] == 0 && area[1] == 0 && area[2] == 0)
            throw std::runtime_error("EXACT_ZERO_FACE_AREA");
        for (int j = 0; j != 3; ++j) {
            std::size_t a = f[j], b = f[(j+1)%3];
            auto& entry = edges[{std::min(a,b),std::max(a,b)}];
            ++entry.first;
            entry.second += a < b ? 1 : -1;
        }
    }
    for (const auto& e : edges) if (e.second.first != 2 || e.second.second != 0)
        throw std::runtime_error("OPEN_OR_MISORIENTED_BOUNDARY");
}

Moments raw_ten(const Geometry& g) {
    constexpr std::array<std::array<int,2>,6> pairs{{{0,0},{1,1},{2,2},{1,2},{0,2},{0,1}}};
    Moments result{};
    for (const Face& f : g.faces) {
        const Point area = area_vector(g.points[f[0]],g.points[f[1]],g.points[f[2]]);
        Point sums{};
        std::array<Rational,6> second{};
        for (std::size_t i : f) {
            const Point& v = g.points[i];
            for (int k = 0; k != 3; ++k) sums[k] += v[k];
            for (int k = 0; k != 6; ++k) second[k] += v[pairs[k][0]]*v[pairs[k][1]];
        }
        Rational constant = 0;
        for (int k = 0; k != 3; ++k) constant += area[k]*g.points[f[0]][k];
        result[0] += constant/6;
        for (int k = 0; k != 3; ++k) result[k+1] += constant*sums[k]/24;
        for (int k = 0; k != 6; ++k) {
            const int p=pairs[k][0], q=pairs[k][1];
            result[k+4] += constant*(sums[p]*sums[q]+second[k])/120;
        }
    }
    if (result[0] <= 0) throw std::runtime_error("NONPOSITIVE_MASS");
    return result;
}

using Tokens = std::vector<std::array<std::string,3>>;
Tokens to_tokens(const Geometry& g) {
    Tokens tokens;
    tokens.reserve(g.points.size());
    for (const Point& v : g.points) tokens.push_back({v[0].get_str(),v[1].get_str(),v[2].get_str()});
    return tokens;
}
Geometry from_tokens(const Tokens& tokens, const std::vector<Face>& faces) {
    Geometry g;
    g.faces = faces;
    g.points.reserve(tokens.size());
    for (const auto& row : tokens) {
        Point p = {Rational(row[0]),Rational(row[1]),Rational(row[2])};
        for (Rational& value : p) value.canonicalize();
        g.points.push_back(std::move(p));
    }
    return g;
}

// Exact immutable source reference; no rational text roundtrip.  The shared
// pointer guarantees lifetime, but does not introduce a Cherchi ABI coupling.
class PreparedMaterial {
    std::shared_ptr<const Geometry> source_;
public:
    explicit PreparedMaterial(std::shared_ptr<const Geometry> source) : source_(std::move(source)) {
        if (!source_) throw std::runtime_error("NULL_EXACT_SOURCE_REF");
        check_boundary(*source_);  // SAME boundary gate as legacy path.
    }
    Moments evaluate_ten() const { return raw_ten(*source_); }
};

std::shared_ptr<const Geometry> tetra_fixture(std::size_t count, int variation) {
    Geometry g;
    g.points.reserve(4*count);
    g.faces.reserve(4*count);
    constexpr std::array<Face,4> boundary{{{0,2,1},{0,1,3},{0,3,2},{1,2,3}}};
    for (std::size_t i=0;i<count;++i) {
        const Rational x(static_cast<long>(3*i),1), y(static_cast<long>(i%7),11);
        const Rational z(static_cast<long>(variation),13);
        const Rational side(static_cast<long>(2+(i+variation)%3),7);
        const std::size_t base=g.points.size();
        g.points.push_back({x,y,z});
        g.points.push_back({x+side,y,z});
        g.points.push_back({x,y+side,z});
        g.points.push_back({x,y,z+side});
        for (Face f : boundary) {
            for (std::size_t& index : f) index+=base;
            g.faces.push_back(f);
        }
    }
    for (Point& v : g.points) for (Rational& coordinate : v) coordinate.canonicalize();
    return std::make_shared<const Geometry>(std::move(g));
}

std::int64_t ns_since(Clock::time_point start) {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count();
}

int main(int argc, char** argv) {
    try {
        if (argc==2 && std::string(argv[1])=="--self-test") {
            auto good=tetra_fixture(1,0);
            if (PreparedMaterial(good).evaluate_ten()[0]!=Rational(4,1029))
                throw std::runtime_error("TETRA_ANALYTIC_VOLUME_DRIFT");
            auto must_reject = [](Geometry bad, const std::string& name) {
                try { PreparedMaterial rejected(std::make_shared<const Geometry>(std::move(bad))); }
                catch (const std::exception& error) {
                    if (std::string(error.what())==name) return;
                    throw;
                }
                throw std::runtime_error("INVALID_GEOMETRY_ACCEPTED:"+name);
            };
            auto misoriented=*good;
            std::swap(misoriented.faces[0][0],misoriented.faces[0][1]);
            must_reject(std::move(misoriented),"OPEN_OR_MISORIENTED_BOUNDARY");
            auto noncanonical=*good;
            noncanonical.points[0][0]=Rational(0,7);
            must_reject(std::move(noncanonical),"NONCANONICAL_SOURCE_RATIONAL");
            auto outofrange=*good;
            outofrange.faces[0][0]=good->points.size();
            must_reject(std::move(outofrange),"FACE_OUT_OF_BOUNDS");
            bool null_rejected=false;
            try { PreparedMaterial missing(std::shared_ptr<const Geometry>{}); }
            catch (const std::exception& error) {
                null_rejected=std::string(error.what())=="NULL_EXACT_SOURCE_REF";
            }
            if (!null_rejected) throw std::runtime_error("NULL_SOURCE_ADMITTED");
            std::cout << "{\"schema\":\"w1-prepared-negative-checks-v1\","
                      << "\"analytic_volume\":\"4/1029\",\"misoriented_rejected\":true,"
                      << "\"noncanonical_rejected\":true,\"out_of_range_rejected\":true,"
                      << "\"null_source_rejected\":true}\n";
            return 0;
        }
        if (argc!=3) throw std::runtime_error("USAGE: prepared_material_probe TETRAHEDRA REPEATS");
        const int tetra=std::stoi(argv[1]), repeats=std::stoi(argv[2]);
        if (tetra<1 || tetra>256 || repeats<1 || repeats>30)
            throw std::runtime_error("OUTSIDE_W1_SMALL_MICROBENCH_LIMITS");
        std::int64_t old_serialize_ns=0,old_parse_ns=0,old_check_ns=0,old_integrate_ns=0;
        std::int64_t new_prepare_ns=0,new_integrate_ns=0;
        Moments first{};
        for (int j=0;j<repeats;++j) {
            // Input construction is identical and outside BOTH timings.
            const std::shared_ptr<const Geometry> source=tetra_fixture(tetra,j);
            auto t=Clock::now();
            const Tokens tokens=to_tokens(*source);
            old_serialize_ns+=ns_since(t);
            t=Clock::now();
            const Geometry old_material=from_tokens(tokens,source->faces);
            old_parse_ns+=ns_since(t);
            t=Clock::now();
            check_boundary(old_material);
            old_check_ns+=ns_since(t);
            t=Clock::now();
            const Moments old_moments=raw_ten(old_material);
            old_integrate_ns+=ns_since(t);

            t=Clock::now();
            const PreparedMaterial prepared(source);
            new_prepare_ns+=ns_since(t);
            t=Clock::now();
            const Moments new_moments=prepared.evaluate_ten();
            new_integrate_ns+=ns_since(t);
            if (old_moments!=new_moments) throw std::runtime_error("GMP_EXACT_TEN_MOMENT_PARITY_FAILED");
            if (j==0) first=new_moments;
        }
        const std::int64_t old_total=old_serialize_ns+old_parse_ns+old_check_ns+old_integrate_ns;
        const std::int64_t new_total=new_prepare_ns+new_integrate_ns;
        std::cout << "{\"schema\":\"w1-prepared-material-microbenchmark-v1\","
                  << "\"scope\":\"ISOLATED_GMP_ROUNDTRIP_ONLY_NOT_SOLVER\","
                  << "\"tetrahedra_per_sample\":" << tetra << ",\"samples\":" << repeats
                  << ",\"vertices_per_sample\":" << 4*tetra
                  << ",\"faces_per_sample\":" << 4*tetra
                  << ",\"old_serialize_ns\":" << old_serialize_ns
                  << ",\"old_parse_ns\":" << old_parse_ns
                  << ",\"old_boundary_gate_ns\":" << old_check_ns
                  << ",\"old_gmp_ten_ns\":" << old_integrate_ns
                  << ",\"prepared_reference_and_gate_ns\":" << new_prepare_ns
                  << ",\"prepared_gmp_ten_ns\":" << new_integrate_ns
                  << ",\"old_total_ns\":" << old_total
                  << ",\"prepared_total_ns\":" << new_total
                  << ",\"exact_ten_moments_equal\":true,"
                  << "\"identical_boundary_gate\":true,"
                  << "\"cherchi_boolean_measured\":false,"
                  << "\"full_solver_measured\":false,"
                  << "\"paper_speed_qualified\":false,\"first_sample_ten_exact\":[";
        for (std::size_t i=0;i<first.size();++i) {
            if (i) std::cout << ',';
            std::cout << '"' << first[i].get_str() << '"';
        }
        std::cout << "]}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "W1_M2_FAILED:" << error.what() << '\n';
        return 1;
    }
}
