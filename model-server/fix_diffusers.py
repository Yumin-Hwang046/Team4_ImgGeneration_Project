#!/usr/bin/env python3
"""
Patch IPAdapterAttnProcessor2_0 in diffusers to fix:
  AttributeError: 'tuple' object has no attribute 'shape'
when encoder_hidden_states is passed as (text_embeds, ip_image_embeds) tuple.
"""
import re
import sys
from pathlib import Path

try:
    import diffusers.models.attention_processor as _m
    src_path = Path(_m.__file__)
    src = src_path.read_text()

    if "_ip_patch_applied" in src:
        print("[fix_diffusers] Already patched, skipping.")
        sys.exit(0)

    # ── Locate IPAdapterAttnProcessor2_0 class ──────────────────────────────
    cls_match = re.search(r"\nclass IPAdapterAttnProcessor2_0", src)
    if not cls_match:
        print("[fix_diffusers] ERROR: IPAdapterAttnProcessor2_0 not found"); sys.exit(1)

    next_cls = re.search(r"\nclass ", src[cls_match.end():])
    cls_end = cls_match.end() + next_cls.start() if next_cls else len(src)
    cls_body = src[cls_match.start():cls_end]

    # ── Patch 1: add early tuple unpack before the .shape access ─────────────
    shape_pat = re.compile(
        r"( {8})(batch_size, sequence_length, _ = \(\s*\n"
        r"\s*hidden_states\.shape if encoder_hidden_states is None else encoder_hidden_states\.shape\s*\n"
        r"\s*\))"
    )
    m1 = shape_pat.search(cls_body)
    if not m1:
        print("[fix_diffusers] ERROR: shape pattern not found in class")
        print(cls_body[cls_body.find("def __call__"):cls_body.find("def __call__") + 2000])
        sys.exit(1)

    indent = m1.group(1)
    early_unpack = (
        f"{indent}# _ip_patch_applied\n"
        f"{indent}_pre_ip = None\n"
        f"{indent}if isinstance(encoder_hidden_states, tuple):\n"
        f"{indent}    encoder_hidden_states, _pre_ip = encoder_hidden_states\n"
        f"{indent}    if not isinstance(_pre_ip, list):\n"
        f"{indent}        _pre_ip = [_pre_ip]\n"
    )
    cls_body = cls_body[: m1.start()] + early_unpack + cls_body[m1.start():]

    # ── Patch 2: guard the original isinstance block that comes later ─────────
    # Original: `if isinstance(encoder_hidden_states, tuple):\n    ...ip_hidden_states = ...`
    orig_check_pat = re.compile(
        r"( {8,12})if isinstance\(encoder_hidden_states, tuple\):\n"
        r"(\s+)(encoder_hidden_states, ip_hidden_states = encoder_hidden_states\n)"
    )
    m2 = orig_check_pat.search(cls_body, m1.start() + len(early_unpack))
    if m2:
        ind1 = m2.group(1)
        ind2 = m2.group(2)
        guarded = (
            f"{ind1}if _pre_ip is not None:\n"
            f"{ind2}ip_hidden_states = _pre_ip\n"
            f"{ind1}elif isinstance(encoder_hidden_states, tuple):\n"
            f"{ind2}{m2.group(3)}"
        )
        cls_body = cls_body[: m2.start()] + guarded + cls_body[m2.end():]
    else:
        print("[fix_diffusers] WARNING: original isinstance block not found — patch 2 skipped")

    new_src = src[: cls_match.start()] + cls_body + src[cls_end:]
    src_path.write_text(new_src)
    print(f"[fix_diffusers] Successfully patched {src_path}")

except Exception as exc:
    import traceback
    traceback.print_exc()
    sys.exit(1)
