cmake_minimum_required(VERSION 3.21)
project(w4_p7_pinned_cherchi_reference_cli LANGUAGES C CXX)
# Build exactly the original public upstream main.cpp. The pinned revision is
# verified in the Action/script, and the external sources stay out of Git.
set(W4_CHERCHI_SOURCE "" CACHE PATH "Exact pinned Cherchi source checkout")
if(NOT EXISTS "${W4_CHERCHI_SOURCE}/main.cpp" OR NOT EXISTS "${W4_CHERCHI_SOURCE}/code/booleans.h")
  message(FATAL_ERROR "Pinned Cherchi checkout is required; no alternate backend")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(TBB_TEST OFF CACHE BOOL "" FORCE)
set(TBB_EXAMPLES OFF CACHE BOOL "" FORCE)
add_subdirectory("${W4_CHERCHI_SOURCE}/arrangements/external/oneTBB" "${CMAKE_BINARY_DIR}/oneTBB")
set(cinolib_DIR "${W4_CHERCHI_SOURCE}/arrangements/external/Cinolib")
set(CINOLIB_USES_OPENGL_GLFW_IMGUI OFF CACHE BOOL "" FORCE)
set(CINOLIB_USES_SHEWCHUK_PREDICATES ON CACHE BOOL "" FORCE)
find_package(cinolib CONFIG REQUIRED)
add_executable(w4_cherchi_reference_native "${W4_CHERCHI_SOURCE}/main.cpp")
target_include_directories(w4_cherchi_reference_native PRIVATE
  "${W4_CHERCHI_SOURCE}"
  "${W4_CHERCHI_SOURCE}/code"
  "${W4_CHERCHI_SOURCE}/arrangements/code"
  "${W4_CHERCHI_SOURCE}/arrangements/external/Indirect_Predicates/include"
  "${W4_CHERCHI_SOURCE}/arrangements/external/abseil-cpp")
target_compile_definitions(w4_cherchi_reference_native PRIVATE TBB_PARALLEL=1)
target_compile_options(w4_cherchi_reference_native PRIVATE -O2 -frounding-math -mavx2)
target_link_libraries(w4_cherchi_reference_native PRIVATE cinolib tbb)
set_target_properties(w4_cherchi_reference_native PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
