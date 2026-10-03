import ipaddress, socket
from urllib.parse import urlsplit, urlunsplit

class UnsafeURLError(ValueError): pass

def validate_public_url(value:str)->str:
    parsed=urlsplit(value)
    if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeURLError("Only public HTTP(S) URLs without embedded credentials are allowed")
    if parsed.port not in {None,80,443}: raise UnsafeURLError("Non-standard ports are blocked")
    try: addresses={item[4][0] for item in socket.getaddrinfo(parsed.hostname,parsed.port or 443,type=socket.SOCK_STREAM)}
    except socket.gaierror as exc: raise UnsafeURLError("Host cannot be resolved") from exc
    for raw in addresses:
        ip=ipaddress.ip_address(raw)
        if not ip.is_global: raise UnsafeURLError("Private, loopback, link-local and reserved hosts are blocked")
    clean=parsed._replace(fragment="")
    return urlunsplit(clean)

