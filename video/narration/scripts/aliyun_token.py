#!/usr/bin/env python3
"""Fetch an Aliyun NLS token using AccessKey ID/Secret (CreateToken RPC API)."""
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
import uuid


def percent_encode(s: str) -> str:
    return (
        urllib.parse.quote(s, safe="")
        .replace("+", "%20")
        .replace("*", "%2A")
        .replace("%7E", "~")
    )


def get_token(ak_id: str, ak_secret: str) -> tuple[str, int]:
    params = {
        "AccessKeyId": ak_id,
        "Action": "CreateToken",
        "Format": "JSON",
        "RegionId": "cn-shanghai",
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(uuid.uuid4()),
        "SignatureVersion": "1.0",
        "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "Version": "2019-02-28",
    }
    sorted_qs = "&".join(
        f"{percent_encode(k)}={percent_encode(params[k])}" for k in sorted(params)
    )
    string_to_sign = "GET&" + percent_encode("/") + "&" + percent_encode(sorted_qs)
    signature = base64.b64encode(
        hmac.new(
            (ak_secret + "&").encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("utf-8")
    params["Signature"] = signature
    query = "&".join(
        f"{percent_encode(k)}={percent_encode(v)}" for k, v in params.items()
    )
    url = "http://nls-meta.cn-shanghai.aliyuncs.com/?" + query
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    tok = data["Token"]
    return tok["Id"], tok["ExpireTime"]


if __name__ == "__main__":
    ak_id = os.environ["ALIYUN_AK_ID"]
    ak_secret = os.environ["ALIYUN_AK_SECRET"]
    token, expire = get_token(ak_id, ak_secret)
    print(token)
