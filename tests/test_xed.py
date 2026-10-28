"""Decode probes for the bundled XED decoder (bin/xed).

Expected iforms captured on 2026-10-28 from XED v2025.06.08, the version
pinned in xed-version.txt (decoder-only build, LONG_64 mode).

If the wheel was built without XED (see CMakeLists.txt) its cases fail
because path('xed') finds no binary.
"""

import re
import subprocess

import pytest

from simdref_llvm_mc import path

# (triple, mattr, extra llvm-mc args, source line, expected iform, expected fields)
CASES = [
    ("x86_64", "+avx512f", ["-x86-asm-syntax=intel"],
     "vmovdqu64 zmm0, zmmword ptr [rdx]",
     "VMOVDQU64_ZMMu64_MASKmskw_MEMu64_AVX512", ["eosz=64"]),
    ("x86_64", "", ["-x86-asm-syntax=intel"],
     "vpclmulhqhqdq xmm0, xmm1, xmm2",
     "VPCLMULQDQ_XMMdq_XMMdq_XMMdq_IMMb", ["eosz=32"]),
    # 66h-prefixed leave: the split's LEAVE_W row keys on eosz 16.
    ("x86_64", "", [], "data16 leave", "LEAVE", ["eosz=16"]),
]


def case_id(c):
    return f"{c[0]}-{c[3][:24]}"


def assemble(triple, mattr, extra, src):
    cmd = [path(), f"-triple={triple}"]
    if mattr:
        cmd.append(f"-mattr={mattr}")
    cmd += [*extra, "-show-encoding"]
    out = subprocess.run(cmd, input=src, capture_output=True, text=True)
    assert out.returncode == 0, f"{triple}: {out.stderr.strip()}"
    # One line can carry several encoding groups (prefix + instruction).
    groups = re.findall(r"encoding: \[([^\]]+)\]", out.stdout)
    assert groups, f"{triple}: no encoding line in {out.stdout!r}"
    return "".join(
        f"{int(b.strip(), 16):02x}" for g in groups for b in g.split(",")
    )


@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_iform(case):
    triple, mattr, extra, src, iform, fields = case
    hexbytes = assemble(triple, mattr, extra, src)
    out = subprocess.run([path("xed")], input=hexbytes + "\n",
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr.strip()
    parts = out.stdout.split()
    assert parts[0] == "OK", f"decode failed: {out.stdout!r}"
    assert parts[2] == iform, f"{src}: got {parts[2]}, want {iform}"
    for f in fields:
        assert f in parts, f"{src}: {f} missing from {out.stdout!r}"
