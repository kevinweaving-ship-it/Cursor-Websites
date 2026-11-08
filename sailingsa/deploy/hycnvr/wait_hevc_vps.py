#!/usr/bin/env python3
"""Pass HEVC Annex-B from stdin to stdout starting at the first VPS.

HYC Cam 5 can emit slices before VPS/SPS. Align the pipe on VPS so ffmpeg
can start. This helper lives with /opt/hycnvr only — not the Voelklip fetch.
"""
import sys

R = sys.stdin.buffer
W = sys.stdout.buffer
START = b"\x00\x00\x00\x01"
buf = b""
found = False
while True:
    chunk = R.read(65536)
    if not chunk:
        break
    buf += chunk
    if not found:
        i = 0
        while True:
            j = buf.find(START, i)
            if j < 0:
                break
            if j + 4 < len(buf) and ((buf[j + 4] >> 1) & 0x3F) == 32:
                buf = buf[j:]
                found = True
                break
            i = j + 1
        if not found:
            if len(buf) > 16:
                buf = buf[-16:]
            continue
    W.write(buf)
    buf = b""
    W.flush()
