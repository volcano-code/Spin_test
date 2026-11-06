cmake_minimum_required(VERSION 3.18)
project(w6_algoim_moment_smoke LANGUAGES CXX)
if(POLICY CMP0169)
  cmake_policy(SET CMP0169 OLD)
endif()
include(FetchContent)

FetchContent_Declare(algoim
  GIT_REPOSITORY https://github.com/algoim/algoim.git
  GIT_TAG da1d81499608e1d499695d255f0233140b8c81e8
  GIT_SHALLOW FALSE
)
FetchContent_GetProperties(algoim)
if(NOT algoim_POPULATED)
  FetchContent_Populate(algoim)
endif()

add_executable(algoim_moment_smoke algoim_moment_smoke.cpp)
target_compile_features(algoim_moment_smoke PRIVATE cxx_std_17)
target_include_directories(algoim_moment_smoke PRIVATE "${algoim_SOURCE_DIR}/algoim")
enable_testing()
add_test(NAME algoim_unit_sphere_raw_moments COMMAND algoim_moment_smoke)
