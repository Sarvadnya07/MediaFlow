import ipaddress
import re
import socket
from urllib.parse import urlparse
from pathlib import Path


class SecurityError(Exception):
    """Exception raised when a security policy or boundary is violated."""
    pass


def validate_and_sanitize_url(url: str, allow_private: bool = False) -> str:
    """
    Validate that a URL is a legitimate HTTP/HTTPS media URL and prevent SSRF.
    Checks:
    1. Scheme must be http or https.
    2. Hostname must be present and not loopback, link-local, multicast, or private RFC1918 (unless allow_private=True).
    3. Prevents user/password embedded credentials in URLs.
    """
    if not url or not isinstance(url, str):
        raise SecurityError("URL must be a non-empty string.")

    cleaned_url = url.strip()
    parsed = urlparse(cleaned_url)

    if parsed.scheme.lower() not in ("http", "https"):
        raise SecurityError(f"Unsupported scheme '{parsed.scheme}'. Only http and https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityError("Invalid URL: missing hostname.")

    if parsed.username or parsed.password:
        raise SecurityError("Embedded credentials in URLs are strictly disallowed.")

    # Check for localhost / loopback aliases
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        if not allow_private:
            raise SecurityError(f"Access to loopback target '{hostname}' is restricted.")

    # IP resolution SSRF verification
    if not allow_private:
        try:
            # Check if hostname is directly an IP literal
            ip_obj = ipaddress.ip_address(hostname)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
                raise SecurityError(f"Restricted private/local IP destination: {hostname}")
        except ValueError:
            # Hostname is a domain name. Resolve addresses to verify they don't map to RFC1918 / loopback
            try:
                addr_info = socket.getaddrinfo(hostname, None)
                for family, _, _, _, sockaddr in addr_info:
                    ip_str = sockaddr[0]
                    resolved_ip = ipaddress.ip_address(ip_str)
                    if resolved_ip.is_private or resolved_ip.is_loopback or resolved_ip.is_link_local or resolved_ip.is_multicast:
                        raise SecurityError(f"Resolved hostname '{hostname}' maps to restricted network IP: {ip_str}")
            except socket.gaierror:
                # If DNS resolution fails here, let yt-dlp handle connectivity error later
                pass

    return cleaned_url


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a suggested filename to prevent directory traversal and remove illegal filesystem characters.
    """
    if not filename:
        return "unnamed_media"

    # Remove any directory path separators and illegal filesystem characters
    clean = re.sub(r'[\\/*?:"<>|]', "_", filename)
    clean = clean.replace("..", "_")
    # Collapse multiple consecutive underscores and trim punctuation
    clean = re.sub(r'_+', '_', clean)
    clean = clean.strip(". _")

    if not clean:
        clean = "unnamed_media"

    if len(clean) > max_length:
        clean = clean[:max_length].strip(". ")

    return clean


def ensure_within_directory(target_path: str | Path, base_directory: str | Path) -> Path:
    """
    Ensure target_path resolves strictly inside base_directory to prevent directory traversal.
    """
    base_dir = Path(base_directory).resolve()
    resolved_target = Path(target_path).resolve()

    try:
        resolved_target.relative_to(base_dir)
    except ValueError:
        raise SecurityError(f"Path traversal detected: '{target_path}' is outside '{base_dir}'.")

    return resolved_target
