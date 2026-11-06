#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include "quadrature_general.hpp"

struct UnitSphere {
  template <typename T>
  T operator()(const algoim::uvector<T, 3>& x) const {
    return x(0)*x(0) + x(1)*x(1) + x(2)*x(2) - T(1);
  }
  template <typename T>
  algoim::uvector<T, 3> grad(const algoim::uvector<T, 3>& x) const {
    return algoim::uvector<T, 3>(T(2)*x(0), T(2)*x(1), T(2)*x(2));
  }
};

int main() {
  const UnitSphere phi;
  const auto box = algoim::HyperRectangle<double, 3>(-1.1, 1.1);
  const auto q = algoim::quadGen<3>(phi, box, -1, -1, 8);
  const std::array<double, 10> got = {
    q([](const auto& x) { return 1.0; }),
    q([](const auto& x) { return x(0); }),
    q([](const auto& x) { return x(1); }),
    q([](const auto& x) { return x(2); }),
    q([](const auto& x) { return x(0)*x(0); }),
    q([](const auto& x) { return x(1)*x(1); }),
    q([](const auto& x) { return x(2)*x(2); }),
    q([](const auto& x) { return x(1)*x(2); }),
    q([](const auto& x) { return x(0)*x(2); }),
    q([](const auto& x) { return x(0)*x(1); })
  };
  const double pi = std::acos(-1.0);
  const std::array<double, 10> expected = {
    4.0*pi/3.0, 0.0, 0.0, 0.0,
    4.0*pi/15.0, 4.0*pi/15.0, 4.0*pi/15.0, 0.0, 0.0, 0.0
  };
  double max_abs_error = 0.0;
  for (std::size_t i = 0; i < got.size(); ++i) {
    max_abs_error = std::max(max_abs_error, std::abs(got[i] - expected[i]));
  }
  std::cout << std::setprecision(17)
            << "{\"source\":\"Algoim\",\"commit\":\"da1d81499608e1d499695d255f0233140b8c81e8\",\"max_abs_error\":"
            << max_abs_error << ",\"moments\":[";
  for (std::size_t i = 0; i < got.size(); ++i) {
    if (i) std::cout << ",";
    std::cout << got[i];
  }
  std::cout << "]}\n";
  return max_abs_error <= 1e-6 ? 0 : 1;
}
