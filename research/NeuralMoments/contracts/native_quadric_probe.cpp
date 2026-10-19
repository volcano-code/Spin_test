// W0-only native probe: compile/link the actual frozen QuadricCoefficients.cpp.
// The unrelated slicer SHA-256 implementation is provided by a test link stub;
// no hash results are asserted or presented as production.
#include "spin/QuadricCoefficients.h"
#include <Eigen/Core>
#include <Eigen/Geometry>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
using Q = spin::QuadricCoefficients10;
using V = Q::Vector;
void ensure(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
void metric(double actual, double expected, double& maximum) {
    const double error = std::abs(actual - expected);
    if (!std::isfinite(error)) throw std::runtime_error("nonfinite native probe output");
    maximum = std::max(maximum, error);
}
}

int main() {
    try {
        double maxValue = 0., maxGradient = 0., maxHomogeneous = 0., maxPullback = 0.;
        double positivePullbackScale = 0.;
        int probes = 0;
        const V raw = (V() << 0.7, -0.1, 0.2, -0.3, 1.1, -0.9, 0.4, 0.6, -0.45, 0.75).finished();
        const Q q = Q::fromUnnormalized(raw);
        const V c = q.values();
        ensure((Q::fromNormalized(c).values().array() == c.array()).all(), "saved c replay changed bits");
        ensure((Q::fromUnnormalized(11.*raw).values()-c).norm() < 5e-16, "positive projective rescaling");
        ensure((Q::fromUnnormalized(-raw).values()+c).norm() < 5e-16, "negative sign is not kept distinct");
        ensure(std::abs(c(7)*c(8)*c(9)) > 1e-8, "cross terms accidentally zero");
        for (int ix=-2;ix<=2;++ix) for (int iy=-2;iy<=2;++iy) for (int iz=-2;iz<=2;++iz) {
            const double x = (ix + 0.31)/3., y = (iy - 0.17)/4., z = (iz+0.43)/5.;
            const Eigen::Vector3d point(x,y,z);
            const double explicitValue = c(0)+c(1)*x+c(2)*y+c(3)*z +
                c(4)*x*x+c(5)*y*y+c(6)*z*z +
                2*c(7)*y*z+2*c(8)*x*z+2*c(9)*x*y;
            metric(q.evaluate(point),explicitValue,maxValue);
            const Eigen::Vector3d grad(c(1)+2*c(4)*x+2*c(8)*z+2*c(9)*y,
                                     c(2)+2*c(5)*y+2*c(7)*z+2*c(9)*x,
                                     c(3)+2*c(6)*z+2*c(7)*y+2*c(8)*x);
            for (int axis=0;axis<3;++axis)
                metric(q.gradient(point)(axis),grad(axis),maxGradient);
            const Eigen::Vector4d p(x,y,z,1.);
            metric(q.evaluate(point),p.dot(q.homogeneousMatrix()*p),maxHomogeneous);
            ++probes;
        }
        const Eigen::Matrix3d linear = (Eigen::AngleAxisd(0.42,Eigen::Vector3d(1.,2.,-1.).normalized()).toRotationMatrix()
                                        * Eigen::DiagonalMatrix<double,3>(1.4,0.8,1.1)).eval();
        const Eigen::Vector3d translation(0.4,-0.2,0.7);
        const Q pulled = q.pullback(linear,translation);
        const double normalizingFactor = (raw.norm()/((pulled.values().norm()))); // ratio from test evaluation below
        (void)normalizingFactor;
        double lastFactor=0.;
        for (int i=0;i<17;++i) {
            const Eigen::Vector3d y(-0.73+0.1*i,0.05+0.07*i,0.31-0.02*i);
            const double old=q.evaluate(linear*y+translation), now=pulled.evaluate(y);
            if (std::abs(old)<1e-4)continue;
            const double factor = now/old;
            ensure(factor>0.,"pullback changed sign");
            if (lastFactor==0.) lastFactor=factor;
            metric(now, lastFactor*old, maxPullback);
        }
        positivePullbackScale=lastFactor;
        ensure(positivePullbackScale>0.,"no positive pullback witnesses");
        ensure(q.inverted().evaluate(Eigen::Vector3d(0.1,0.2,0.3)) ==
               -q.evaluate(Eigen::Vector3d(0.1,0.2,0.3)),"inverted halfspace");
        bool zeroRejected=false,nonfiniteRejected=false,singularRejected=false;
        try { (void)Q::fromUnnormalized(V::Zero()); } catch (const std::invalid_argument&) { zeroRejected=true; }
        V bad=raw;bad(0)=std::numeric_limits<double>::quiet_NaN();
        try { (void)Q::fromUnnormalized(bad); } catch (const std::invalid_argument&) { nonfiniteRejected=true; }
        try { (void)q.pullback(Eigen::Matrix3d::Zero(),Eigen::Vector3d::Zero()); }
        catch (const std::invalid_argument&) { singularRejected=true; }
        ensure(zeroRejected&&nonfiniteRejected&&singularRejected,"bad native inputs not rejected");
        ensure(maxValue<2e-14&&maxGradient<2e-14&&maxHomogeneous<2e-14&&maxPullback<2e-13,
               "native coefficient/matrix order mismatch");
        std::cout<<std::setprecision(17)<<"{\"status\":\"PASS\",\"probe_points\":"<<probes
                 <<",\"max_value_error\":"<<maxValue<<",\"max_gradient_error\":"<<maxGradient
                 <<",\"max_homogeneous_error\":"<<maxHomogeneous<<",\"max_pullback_error\":"<<maxPullback
                 <<",\"positive_pullback_scale\":"<<positivePullbackScale
                 <<",\"hash_dependency_stubbed\":true}"<<std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr<<"W0 NATIVE FAILURE: "<<error.what()<<std::endl;
        return 1;
    }
}
