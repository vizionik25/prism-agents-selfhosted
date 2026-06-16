import datetime
from jose import jwt

# RSA Private Key
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAtvyeraLbCWxANHVz+X3kFrpZPIxgo/a3q3sVunVV32x7g43X
yBLrGT/+fX1ghTArV4C5q1GwMLQTYWXi0ziy19uLgd19DCxGxAYpeQ9Z52d/unZ+
LryJ5k6nSYMcgHeaaNsJohX5pCOJ/9sjSa9VyFsZ34IpCRmbQFXnN5VqrMYxhlq0
oySwslFrgRaTJgSQ/fLrQBg9IJzrNKWCBQpfi3hJ3dLrrBILmQf1D4oilqPu1gqp
8rGGzFOf0zYXN6n7+W239EWh/KY7k6bufgcao8OxgGQUdD2TT6bl7hZrlXzPDSwa
1vg/1MppqXdeev4YC/mrbVwYDUWTgFQY1J3ToQIDAQABAoIBAAMyyC09xvlTsI2a
LfRC7I0vJacmxvumsNAo/xi6u00D7ua+QHLJTd2rni2gVuMNE/zcDaK+c0duplYR
+1R4zbtzJW2YKvre/T+o4emxSH+Ach2Wu57igcCKSGdDCOj/7i1+Ap2YJ7xkOKHF
uUis7WFqojmjY0c68Nk/hyKUFIC/kHSI/DjVKquHFhGfszk2eLyBuBMAvTistGYd
s3XuwQaw050tJ5uMXjwGwlZlIOLjRiEzsCuzJmlVdku+HZJIhoPR+Hq76DeBnFai
9abtEVrzDqtMpqNlexKuggwLzOqnnFgr4VBVFL8YexuJvr7oa/V3RLkxMo57V0dv
/hJxjqcCgYEA954zhGWmc8aZe75VEnPiY+9+kDRx2be8tdhwVorwG3WdajyRoRlS
RnX23xzymmVzdJCORWhkDKCyASCw4uCLR4xCLZehV2sw92gxLFG0s+RD0ZouxIik
8Sj9vzyzNaQcL62GKTsluX0ogtZM7Dk9oj757b137r5KrvDcx9cuTycCgYEAvS5X
EXCyFeEoU7j5aFsLDo5L/7P5eVSOLHX/Z60CQC/P2tMIILyLvzz+AiKJY8LAu2wT
1MD7/iQPqAmy1iotnIxZZjk+uqoUa8hj7VS5JAjSUDtIqEwdRwuZ5zYrrvgTaMfa
WpkqADaBkBvxSG5pOEGbPjLevf8bkyZ649UuA/cCgYB0qY+CGFZFA9O6TmFMcVa/
WM3baSoetodtcYzz6T/Y4CALNoAyU3jFA70NP1k5zwSHbbfqEZXZsThMebd9HOfi
DL39Nwxn4HPQjMFmLRSjEK+3KBpStEJp8LMkj5erdSdmey3TbS+H5eTZR9g0D3/v
WhZsoTDJRdRv+cE7UjFaTwKBgQCjoOpENnKCRC5qQ+rNXTnyDBgmAhf83qreP+16
UgVJWVFyFufH0O0aqvmVBSRKek/TjEaW1ZjgF3bHRCQ/41lyN1638TmVoLhrBXeQ
9p/wUAUAylYs4zDLm3gxqQQdoYrALWRqymGur3ZfHBwVJxKxSuWo5b0NHxNNspHG
cEQNvwKBgCPN93WvcgbQpPOV6TMP+tJwzj2h8NJjU83uxIrpDalT8X9YdIEJeHPc
Y3huGKIaegUSQOSyLw77ZAUQiCdjf6f6/YmIZX1D5s3TfCJTrYAH1Mx24RpYLohA
rAUrwJJwhOzMhq73IZT6xJasWaXj6CSsE8dhfpDR/ieFDFpLOH7X
-----END RSA PRIVATE KEY-----"""


def generate_license(tier="ENTERPRISE", organization="Acme Corp", domain="localhost", days=365):
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)
    payload = {
        "iss": "prism-agents.com",
        "sub": "prism-license-key",
        "tier": tier,
        "expires_at": exp.isoformat().replace("+00:00", "Z"),
        "organization": organization,
        "self_hosted_domain": domain,
    }
    token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
    print(f"License Key generated for {organization} (Tier: {tier}, Domain: {domain}, Expires: {payload['expires_at']})")
    print(token)
    return token


if __name__ == "__main__":
    import sys
    tier = "ENTERPRISE"
    org = "Self-Hosted Community"
    domain = "localhost"
    if len(sys.argv) > 1:
        tier = sys.argv[1]
    if len(sys.argv) > 2:
        org = sys.argv[2]
    if len(sys.argv) > 3:
        domain = sys.argv[3]
    generate_license(tier, org, domain)
