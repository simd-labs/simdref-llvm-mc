# simdref-llvm-mc

This package ships the `llvm-mc` assembler from the LLVM project as a pip
wheel. It covers the X86, AArch64 and RISCV targets. It is built from the
official llvm-project source release.

## Install

```
pip install simdref-llvm-mc
```

## Usage

Run the assembler from the command line:

```
simdref-llvm-mc -triple=aarch64 -show-encoding
```

Get the binary path from Python:

```python
import simdref_llvm_mc
simdref_llvm_mc.path()
```

The wheel version is the pinned LLVM release, for example `23.1.4`. A rebuild
against the same LLVM release adds `.postN`, for example `23.1.4.post1`.
The file `llvm-version.txt` in the source tree holds the release tag on
line 1 and the sha256 of the source tarball on line 2.

## Build from source

```
uv build --wheel
```

The build downloads the pinned tarball and checks its sha256. Set
`LLVM_MC_TARBALL=/path/to/llvm-project-<version>.src.tar.xz` to use a
local copy.

## License

Apache-2.0 WITH LLVM-exception. See `LICENSE`.
