"""W6 P-CRAFT-inspired U-FNO-Moment research-only smoke interface."""
from .model import (CachedGeometry, FactorizedSpectralConv3d,
                    UFNOGeometryEncoder, UFNOMoment, canonical_geometry,
                    count_real_parameters, positive_projective_coefficients)
from .adaptation import ResidualAdapter

__all__ = ["CachedGeometry", "FactorizedSpectralConv3d", "UFNOGeometryEncoder",
           "UFNOMoment", "canonical_geometry", "count_real_parameters",
           "positive_projective_coefficients", "ResidualAdapter"]
