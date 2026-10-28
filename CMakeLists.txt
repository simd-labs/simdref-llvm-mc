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
# Forward cross-compilation settings (macOS arm64 -> x86_64, toolchains).
set(_fwd_args)
foreach(_var CMAKE_OSX_ARCHITECTURES CMAKE_OSX_DEPLOYMENT_TARGET
             CMAKE_OSX_SYSROOT CMAKE_TOOLCHAIN_FILE
             CMAKE_C_COMPILER CMAKE_CXX_COMPILER CMAKE_MAKE_PROGRAM)
  if(DEFINED ${_var} AND NOT "${${_var}}" STREQUAL "")
    list(APPEND _fwd_args "-D${_var}=${${_var}}")
  endif()
endforeach()

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
if(NOT WIN32)
  install(CODE "execute_process(COMMAND strip \"\${CMAKE_INSTALL_PREFIX}/simdref_llvm_mc/llvm-mc\")")
endif()
