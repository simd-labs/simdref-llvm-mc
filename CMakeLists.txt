cmake_minimum_required(VERSION 3.26)
# Version pin comes from llvm-version.txt: tag on line 1, sha256 on line 2.
project(simdref_llvm_mc NONE)

file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/llvm-version.txt" LLVM_PIN LIMIT_COUNT 2)
list(LENGTH LLVM_PIN _len)
if(NOT _len EQUAL 2)
  message(FATAL_ERROR "llvm-version.txt needs exactly two lines: release tag, then sha256")
endif()
list(GET LLVM_PIN 0 LLVM_TAG)
list(GET LLVM_PIN 1 LLVM_SHA256)
string(REGEX REPLACE "^llvmorg-" "" LLVM_VERSION "${LLVM_TAG}")

# XED pins come from xed-version.txt: xed tag, xed sha256, mbuild tag, mbuild sha256.
file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/xed-version.txt" XED_PIN LIMIT_COUNT 4)
list(LENGTH XED_PIN _xlen)
if(NOT _xlen EQUAL 4)
  message(FATAL_ERROR "xed-version.txt needs exactly four lines: xed tag, xed sha256, mbuild tag, mbuild sha256")
endif()
list(GET XED_PIN 0 XED_TAG)
list(GET XED_PIN 1 XED_SHA256)
list(GET XED_PIN 2 MBUILD_TAG)
list(GET XED_PIN 3 MBUILD_SHA256)

# Pre-downloaded tarball (CI cache). Falls back to the GitHub release URL when
# the file is absent, so the same config works with a cache miss.
set(LLVM_MC_TARBALL "$ENV{LLVM_MC_TARBALL}" CACHE FILEPATH
    "Pre-downloaded llvm-project source tarball")
if(LLVM_MC_TARBALL AND EXISTS "${LLVM_MC_TARBALL}")
  get_filename_component(_llvm_url "${LLVM_MC_TARBALL}" ABSOLUTE
                         BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
else()
  if(LLVM_MC_TARBALL)
    message(WARNING "LLVM_MC_TARBALL set but absent: ${LLVM_MC_TARBALL}; downloading")
  endif()
  set(_llvm_url
      "https://github.com/llvm/llvm-project/releases/download/${LLVM_TAG}/llvm-project-${LLVM_VERSION}.src.tar.xz")
endif()

# Inner build config goes through an initial-cache file: passing lists with
# semicolons through ExternalProject's CMAKE_ARGS is fragile in Ninja mode.
set(_init "${CMAKE_BINARY_DIR}/llvm-init.cmake")
file(WRITE "${_init}" "
set(CMAKE_BUILD_TYPE Release CACHE STRING \"\" FORCE)
set(LLVM_TARGETS_TO_BUILD \"X86;AArch64;RISCV\" CACHE STRING \"\" FORCE)
set(LLVM_ENABLE_PROJECTS \"\" CACHE STRING \"\" FORCE)
set(LLVM_ENABLE_RUNTIMES \"\" CACHE STRING \"\" FORCE)
set(LLVM_ENABLE_ZLIB OFF CACHE BOOL \"\" FORCE)
set(LLVM_ENABLE_ZSTD OFF CACHE BOOL \"\" FORCE)
set(LLVM_ENABLE_TERMINFO OFF CACHE BOOL \"\" FORCE)
set(LLVM_ENABLE_LIBXML2 OFF CACHE BOOL \"\" FORCE)
set(LLVM_INCLUDE_TESTS OFF CACHE BOOL \"\" FORCE)
set(LLVM_INCLUDE_EXAMPLES OFF CACHE BOOL \"\" FORCE)
set(LLVM_INCLUDE_BENCHMARKS OFF CACHE BOOL \"\" FORCE)
set(LLVM_INCLUDE_DOCS OFF CACHE BOOL \"\" FORCE)
set(LLVM_INCLUDE_UTILS OFF CACHE BOOL \"\" FORCE)
set(LLVM_ENABLE_BINDINGS OFF CACHE BOOL \"\" FORCE)
set(LLVM_BUILD_STATIC OFF CACHE BOOL \"\" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL \"\" FORCE)
set(LLVM_ENABLE_LTO OFF CACHE BOOL \"\" FORCE)
set(LLVM_ENABLE_WERROR OFF CACHE BOOL \"\" FORCE)
")

# Static libstdc++/libgcc keeps the binary free of C++ runtime deps on Linux.
if(UNIX AND NOT APPLE)
  file(APPEND "${_init}" "
set(CMAKE_EXE_LINKER_FLAGS \"-static-libstdc++ -static-libgcc\" CACHE STRING \"\" FORCE)
")
endif()
# Static CRT (/MT) keeps the Windows exe free of the VC++ redistributable.
if(WIN32)
  file(APPEND "${_init}" "
set(CMAKE_MSVC_RUNTIME_LIBRARY \"MultiThreaded\" CACHE STRING \"\" FORCE)
")
endif()
# Forward cross-compilation settings (macOS arm64 -> x86_64, toolchains).
set(_fwd_args)
foreach(_var CMAKE_OSX_ARCHITECTURES CMAKE_OSX_DEPLOYMENT_TARGET
             CMAKE_OSX_SYSROOT CMAKE_TOOLCHAIN_FILE
             CMAKE_C_COMPILER CMAKE_CXX_COMPILER CMAKE_MAKE_PROGRAM)
  if(DEFINED ${_var} AND NOT "${${_var}}" STREQUAL "")
    list(APPEND _fwd_args "-D${_var}=${${_var}}")
  endif()
endforeach()

# mfile.py (XED's build driver) runs under this interpreter too.
find_package(Python3 REQUIRED COMPONENTS Interpreter)

if(WIN32)
  # The runner PATH has a `ninja` shim that prints the MSBuild banner; take the
  # real binary shipped by the pip `ninja` package in the build environment.
  execute_process(
    COMMAND "${Python3_EXECUTABLE}" -c
      "import ninja, os; print(os.path.join(ninja.BIN_DIR, 'ninja.exe'))"
    OUTPUT_VARIABLE _ninja
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE _ninja_rc)
  if(_ninja_rc OR NOT EXISTS "${_ninja}")
    message(FATAL_ERROR "ninja from the pip package not found (rc=${_ninja_rc}): ${_ninja}")
  endif()
  list(APPEND _fwd_args "-DCMAKE_MAKE_PROGRAM=${_ninja}")
endif()

if(WIN32)
  set(_exe "llvm-mc.exe")
else()
  set(_exe "llvm-mc")
endif()
set(_llvm_bin "${CMAKE_BINARY_DIR}/llvm-build/bin/${_exe}")

include(ExternalProject)
ExternalProject_Add(llvm-project
  URL "${_llvm_url}"
  URL_HASH "SHA256=${LLVM_SHA256}"
  DOWNLOAD_EXTRACT_TIMESTAMP FALSE
  SOURCE_SUBDIR llvm
  BINARY_DIR "${CMAKE_BINARY_DIR}/llvm-build"
  # Pin Ninja: the MSVC multi-config generator puts llvm-mc.exe under
  # <Config>/bin, but the install(FILES) path assumes single-config bin/.
  CMAKE_GENERATOR "Ninja"
  CMAKE_ARGS -C "${_init}" ${_fwd_args}
  BUILD_COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --config Release --target llvm-mc --parallel
  INSTALL_COMMAND ""
  BUILD_BYPRODUCTS "${_llvm_bin}"
  USES_TERMINAL_DOWNLOAD TRUE
  USES_TERMINAL_CONFIGURE TRUE
  USES_TERMINAL_BUILD TRUE
)

install(FILES "${_llvm_bin}"
        DESTINATION simdref_llvm_mc
        PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
                    GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)

# XED decoder-only static library, built by XED's own mfile.py (mbuild). The
# vendored mbuild tree shadows the real mbuild package as a namespace package
# on Python 3.14, hence PYTHONPATH in the build step below.
set(_xed_src "${CMAKE_BINARY_DIR}/xed-src")
set(_mbuild_src "${CMAKE_BINARY_DIR}/mbuild-src")
set(_xed_kit "${_xed_src}/obj/wkit")

ExternalProject_Add(mbuild-src
  URL "https://github.com/intelxed/mbuild/archive/refs/tags/${MBUILD_TAG}.tar.gz"
  URL_HASH "SHA256=${MBUILD_SHA256}"
  DOWNLOAD_EXTRACT_TIMESTAMP FALSE
  SOURCE_DIR "${_mbuild_src}"
  CONFIGURE_COMMAND ""
  BUILD_COMMAND ""
  INSTALL_COMMAND ""
  USES_TERMINAL_DOWNLOAD TRUE
)

set(_xed_mfile "${Python3_EXECUTABLE}" mfile.py --static --opt=2 --no-encoder)
if(APPLE)
  set(_xed_ccflags "")
  if(CMAKE_OSX_ARCHITECTURES)
    # mfile bypasses CMake's compiler flags; pass the target arch directly
    # (the macos-x86_64 wheel cross-builds XED on an arm64 runner).
    string(APPEND _xed_ccflags " -arch ${CMAKE_OSX_ARCHITECTURES}")
  endif()
  if(CMAKE_OSX_DEPLOYMENT_TARGET)
    string(APPEND _xed_ccflags " -mmacosx-version-min=${CMAKE_OSX_DEPLOYMENT_TARGET}")
  endif()
  if(_xed_ccflags)
    string(STRIP "${_xed_ccflags}" _xed_ccflags)
    list(APPEND _xed_mfile "--extra-ccflags=${_xed_ccflags}")
  endif()
endif()
if(WIN32)
  set(_xed_libs "${_xed_kit}/lib/xed.lib" "${_xed_kit}/lib/xed-ild.lib")
else()
  set(_xed_libs "${_xed_kit}/lib/libxed.a" "${_xed_kit}/lib/libxed-ild.a")
endif()

ExternalProject_Add(xed-project
  URL "https://github.com/intelxed/xed/archive/refs/tags/${XED_TAG}.tar.gz"
  URL_HASH "SHA256=${XED_SHA256}"
  DOWNLOAD_EXTRACT_TIMESTAMP FALSE
  SOURCE_DIR "${_xed_src}"
  CONFIGURE_COMMAND ""
  BUILD_COMMAND "${CMAKE_COMMAND}" -E copy_directory "${_mbuild_src}" "${_xed_src}/mbuild"
  COMMAND "${CMAKE_COMMAND}" -E env "PYTHONPATH=${_xed_src}/mbuild"
          "${CMAKE_COMMAND}" -E chdir "${_xed_src}" ${_xed_mfile}
  INSTALL_COMMAND ""
  BUILD_BYPRODUCTS ${_xed_libs}
  DEPENDS mbuild-src
  USES_TERMINAL_DOWNLOAD TRUE
  USES_TERMINAL_BUILD TRUE
)

# bin/xed: hex bytes on stdin -> XED iclass, iform and decode facts.
enable_language(C)
add_executable(xed-tool xedform.c)
set_target_properties(xed-tool PROPERTIES OUTPUT_NAME xed)
add_dependencies(xed-tool xed-project)
target_include_directories(xed-tool PRIVATE "${_xed_kit}/include")
# The two XED archives share objects; libxed.a must come first.
target_link_libraries(xed-tool PRIVATE ${_xed_libs})
if(WIN32)
  # Static CRT (/MT) keeps the Windows exe free of the VC++ redistributable.
  set_property(TARGET xed-tool PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded")
endif()

install(TARGETS xed-tool RUNTIME DESTINATION simdref_llvm_mc)
if(NOT WIN32)
  install(CODE "execute_process(COMMAND strip \"\${CMAKE_INSTALL_PREFIX}/simdref_llvm_mc/llvm-mc\" \"\${CMAKE_INSTALL_PREFIX}/simdref_llvm_mc/xed\")")
endif()
