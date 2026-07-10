#!/usr/bin/env python3
"""Synthesize speech via Aliyun NLS RESTful TTS API.

Usage: aliyun_tts.py <voice> <text> <out.mp3> [speech_rate]
Reads ALIYUN_AK_ID / ALIYUN_AK_SECRET / ALIYUN_APPKEY from env.
Token is cached in /tmp/aliyun_nls_token.json until near expiry.
"""
import json
import os
import sys
import time
import urllib.request

from aliyun_token import get_token

TOKEN_CACHE = "/tmp/aliyun_nls_token.json"


def cached_token(ak_id: str, ak_secret: str) -> str:
    if os.path.exists(TOKEN_CACHE):
        try:
            with open(TOKEN_CACHE) as f:
                c = json.load(f)
            if c["expire"] - time.time() > 120:
                return c["token"]
        except Exception:
            pass
    token, expire = get_token(ak_id, ak_secret)
    with open(TOKEN_CACHE, "w") as f:
        json.dump({"token": token, "expire": expire}, f)
    return token


def synth(voice: str, text: str, out_path: str, speech_rate: int = 0) -> None:
    ak_id = os.environ["ALIYUN_AK_ID"]
    ak_secret = os.environ["ALIYUN_AK_SECRET"]
    appkey = os.environ["ALIYUN_APPKEY"]
    token = cached_token(ak_id, ak_secret)

    url = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts"
    body = {
        "appkey": appkey,
        "token": token,
        "text": text,
        "format": "mp3",
        "sample_rate": 24000,
        "voice": voice,
        "volume": 50,
        "speech_rate": speech_rate,
        "pitch_rate": 0,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        ctype = resp.headers.get("Content-Type", "")
        data = resp.read()
    if "audio" not in ctype:
        sys.stderr.write("ERROR response: " + data.decode("utf-8", "ignore") + "\n")
        sys.exit(1)
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"OK {out_path} ({len(data)} bytes)")


if __name__ == "__main__":
    voice, text, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    rate = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    synth(voice, text, out_path, rate)
