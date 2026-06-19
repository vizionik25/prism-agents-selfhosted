from datetime import datetime, timezone
from jose import jwt, JWTError
from media_agents.env import PRISM_LICENSE_KEY

LICENSE_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtvyeraLbCWxANHVz+X3k
FrpZPIxgo/a3q3sVunVV32x7g43XyBLrGT/+fX1ghTArV4C5q1GwMLQTYWXi0ziy
19uLgd19DCxGxAYpeQ9Z52d/unZ+LryJ5k6nSYMcgHeaaNsJohX5pCOJ/9sjSa9V
yFsZ34IpCRmbQFXnN5VqrMYxhlq0oySwslFrgRaTJgSQ/fLrQBg9IJzrNKWCBQpf
i3hJ3dLrrBILmQf1D4oilqPu1gqp8rGGzFOf0zYXN6n7+W239EWh/KY7k6bufgca
o8OxgGQUdD2TT6bl7hZrlXzPDSwa1vg/1MppqXdeev4YC/mrbVwYDUWTgFQY1J3T
oQIDAQAB
-----END PUBLIC KEY-----"""


class LicenseService:
    @staticmethod
    def get_license_claims() -> dict | None:
        if not PRISM_LICENSE_KEY:
            return None
        try:
            claims = jwt.decode(
                PRISM_LICENSE_KEY, LICENSE_PUBLIC_KEY, algorithms=["RS256"]
            )
            # Verify expiration
            exp = claims.get("expires_at")
            if exp:
                try:
                    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > exp_dt:
                        return None
                except ValueError:
                    return None
            return claims
        except JWTError:
            return None

    @staticmethod
    def has_enterprise_license() -> bool:
        claims = LicenseService.get_license_claims()
        return claims is not None and claims.get("tier") == "ENTERPRISE"
