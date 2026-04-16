import ipaddress
import socket
from urllib.parse import urlparse

from ocr_processor.config import settings
from ocr_processor.domain.exceptions import (
    FileTooLargeError,
    InvalidFileTypeError,
    UnsafeURLError,
)

# Private/reserved IP networks (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),   # shared address space
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return any(ip in net for net in _BLOCKED_NETWORKS)
    except ValueError:
        return True  # unparseable → block


def validate_file(content_type: str, size_bytes: int) -> None:
    """Validate that a file has an allowed type and does not exceed the size limit."""
    if content_type not in settings.allowed_mime_types:
        raise InvalidFileTypeError(content_type)
    if size_bytes > settings.max_file_size_bytes:
        raise FileTooLargeError(size_bytes, settings.max_file_size_bytes)


def validate_url(url: str) -> None:
    """Validate that a URL is safe to fetch (scheme + SSRF checks)."""
    parsed = urlparse(url)

    if parsed.scheme not in settings.allowed_url_schemes:
        raise UnsafeURLError(f"scheme '{parsed.scheme}' is not allowed")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("missing hostname")

    # Block known metadata endpoints by hostname
    blocked_hostnames = {
        "metadata.google.internal",
        "169.254.169.254",
        "fd00:ec2::254",
    }
    if hostname.lower() in blocked_hostnames:
        raise UnsafeURLError(f"hostname '{hostname}' is blocked")

    # Resolve all IPs and check each one
    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"cannot resolve hostname '{hostname}': {exc}") from exc

    for _family, _type, _proto, _canonname, sockaddr in results:
        ip_str = sockaddr[0]
        if _is_private_ip(ip_str):
            raise UnsafeURLError(
                f"hostname '{hostname}' resolves to private address '{ip_str}'"
            )
