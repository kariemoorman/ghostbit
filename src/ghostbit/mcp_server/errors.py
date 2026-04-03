import html
import io
import logging
import os
import re
import sys
import subprocess
import unicodedata
from contextlib import contextmanager
from typing import Any, Generator

from ghostbit.audiostego.core.audio_steganography import EncodeMode

logger = logging.getLogger("ghostbit.mcp_server")

# --- Constants --- #

AUDIO_INPUT_EXTENSIONS = {".wav", ".flac", ".mp3", ".m4a", ".aiff", ".aif"}
AUDIO_OUTPUT_EXTENSIONS = {".wav", ".flac", ".m4a", ".aiff", ".aif"}
IMAGE_EXTENSIONS = {
    ".png",
    ".bmp",
    ".tiff",
    ".tif",
    ".jpeg",
    ".jpg",
    ".gif",
    ".webp",
    ".avif",
    ".heic",
    ".svg",
}
ALL_EXTENSIONS = AUDIO_INPUT_EXTENSIONS | IMAGE_EXTENSIONS

MAX_FILE_SIZE_BYTES = 1_073_741_824  # 1 GB
MAX_FILENAME_LENGTH = 128

QUALITY_MAP = {
    "low": EncodeMode.LOW_QUALITY,
    "normal": EncodeMode.NORMAL_QUALITY,
    "high": EncodeMode.HIGH_QUALITY,
}


# --- Filesystem Sandbox --- #


def _load_allowed_dirs() -> list[str] | None:
    """Load allowed directory list from GHOSTBIT_ALLOWED_DIRS environment variable.

    Format: colon-separated list of absolute directory paths.
    Example: GHOSTBIT_ALLOWED_DIRS=/home/user/stego:/tmp/ghostbit

    If not set, returns None (sandboxing disabled — all paths allowed).
    If set to empty string, returns empty list (all paths blocked).
    """
    env_val = os.environ.get("GHOSTBIT_ALLOWED_DIRS")
    if env_val is None:
        return None
    if not env_val.strip():
        return []
    dirs = [
        os.path.realpath(os.path.abspath(d.strip()))
        for d in env_val.split(":")
        if d.strip()
    ]
    return dirs


ALLOWED_DIRS: list[str] | None = _load_allowed_dirs()


def validate_path_in_sandbox(path: str, label: str = "Path") -> None:
    """Enforce filesystem sandboxing if GHOSTBIT_ALLOWED_DIRS is configured.

    Verifies that the resolved path falls within one of the allowed directories.
    This prevents tools from reading/writing outside the designated sandbox.

    If GHOSTBIT_ALLOWED_DIRS is not set, this check is a no-op (all paths allowed).
    """
    if ALLOWED_DIRS is None:
        return  # Sandboxing not configured

    resolved = os.path.realpath(os.path.abspath(path))

    for allowed in ALLOWED_DIRS:
        # Check if resolved path starts with allowed dir (with trailing separator)
        if resolved == allowed or resolved.startswith(allowed + os.sep):
            return

    allowed_display = ", ".join(ALLOWED_DIRS) if ALLOWED_DIRS else "(none)"
    raise GhostbitMCPError(
        f"{label} is outside the allowed directories. " f"Allowed: {allowed_display}"
    )


# --- Exceptions --- #


class GhostbitMCPError(Exception):
    """Safe, user-facing error for MCP tool responses.

    Messages from this exception are returned directly to the MCP client.
    They must NEVER contain file contents, passwords, or stack traces.
    """

    pass


# --- Stdout Capture (Protocol Integrity) --- #


@contextmanager
def capture_stdout() -> Generator[io.StringIO, None, None]:
    """Redirect sys.stdout and sys.stdin during coder calls.

    The existing AudioMultiFormatCoder and ImageMultiFormatCoder classes print
    formatted CLI output to stdout. Since MCP stdio transport uses stdout for
    JSON-RPC protocol messages, any stray print() would corrupt the transport.

    Also redirects stdin to prevent any input() calls from blocking the server
    (e.g., ImageMultiFormatCoder.encode() prompts "Continue without password?").

    Usage:
        with capture_stdout() as output:
            coder.encode_files_multi_format(...)
        captured_text = output.getvalue()  # optional supplementary info
    """
    old_stdout = sys.stdout
    old_stdin = sys.stdin
    sys.stdout = buffer = io.StringIO()
    sys.stdin = io.StringIO("")  # empty stdin — input() returns "" immediately
    try:
        yield buffer
    finally:
        sys.stdout = old_stdout
        sys.stdin = old_stdin


# --- Path Normalization & Sanitization --- #


def normalize_path(path: str) -> str:
    """Normalize a path to its absolute, resolved form.

    Resolves symlinks, '..' sequences, and relative paths. This ensures
    all subsequent validation operates on the true filesystem target.
    """
    return os.path.realpath(os.path.abspath(path))


def validate_not_symlink(path: str, label: str = "File") -> None:
    """Reject symbolic links to prevent symlink-based attacks.

    Symlinks could redirect reads to sensitive files (e.g., /etc/shadow)
    or writes to unintended locations.
    """
    if os.path.islink(path):
        raise GhostbitMCPError(
            f"{label} is a symbolic link, which is not allowed for security reasons: {path}"
        )


def sanitize_input_path(path: str) -> str:
    """4-pass input sanitization pipeline for file paths.

    Pass 1: Normalize to absolute real path (resolve symlinks, ..)
    Pass 2: Reject null bytes and control characters
    Pass 3: Reject shell metacharacters that could enable injection
    Pass 4: Reject paths with suspicious patterns

    Returns the sanitized, normalized path.
    """
    # Pass 1: Reject null bytes and control characters (BEFORE normalization,
    # because Python 3.14+ raises ValueError from realpath on null bytes)
    if "\x00" in path:
        raise GhostbitMCPError("Path contains null bytes")
    if any(
        unicodedata.category(c).startswith("C") and c not in ("\n", "\r", "\t")
        for c in path
    ):
        raise GhostbitMCPError("Path contains control characters")

    # Pass 2: Normalize to absolute real path
    cleaned = normalize_path(path)

    # Pass 3: Reject shell metacharacters (command injection prevention)
    shell_chars = set("|;&$`!><")
    if shell_chars & set(path):
        raise GhostbitMCPError(
            f"Path contains disallowed characters: "
            f"{', '.join(repr(c) for c in sorted(shell_chars & set(path)))}"
        )

    # Pass 4: Reject suspicious path patterns
    if ".." in os.path.basename(path):
        raise GhostbitMCPError("Path contains '..' in filename component")

    return cleaned


# --- Input Validation --- #


def validate_file_exists(path: str, label: str = "File") -> str:
    """Validate that a file path exists, is a regular file, is not a symlink,
    and falls within the filesystem sandbox (if configured).

    Returns the normalized, sanitized path.
    Raises GhostbitMCPError with a safe message (path only, no contents).
    """
    cleaned = sanitize_input_path(path)
    validate_path_in_sandbox(cleaned, label)
    if not os.path.exists(cleaned):
        raise GhostbitMCPError(f"{label} not found: {path}")
    if not os.path.isfile(cleaned):
        raise GhostbitMCPError(f"{label} is not a file: {path}")
    validate_not_symlink(cleaned, label)
    return cleaned


def validate_file_extension(path: str, allowed: set[str], label: str = "File") -> None:
    """Validate that a file has an allowed extension.

    Args:
        path: File path to check.
        allowed: Set of lowercase extensions including the dot (e.g., {".wav", ".flac"}).
        label: Human-readable label for error messages.

    Raises GhostbitMCPError listing the allowed formats.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in allowed:
        sorted_exts = sorted(allowed)
        raise GhostbitMCPError(
            f"{label} has unsupported format '{ext}'. "
            f"Supported: {', '.join(sorted_exts)}"
        )


def validate_file_size(
    path: str, max_bytes: int = MAX_FILE_SIZE_BYTES, label: str = "File"
) -> None:
    """Reject files exceeding the size limit before loading into memory.

    Prevents resource exhaustion from degenerate inputs.
    """
    size = os.path.getsize(path)
    if size > max_bytes:
        size_mb = size / (1024 * 1024)
        max_mb = max_bytes / (1024 * 1024)
        raise GhostbitMCPError(
            f"{label} is too large ({size_mb:.1f} MB). "
            f"Maximum allowed: {max_mb:.0f} MB"
        )


def validate_directory_writable(path: str) -> str:
    """Ensure the output path's parent directory exists, is writable,
    and falls within the filesystem sandbox (if configured).

    Normalizes the path first to prevent path traversal attacks.
    Returns the normalized path.
    """
    cleaned = sanitize_input_path(path)
    validate_path_in_sandbox(cleaned, "Output path")
    dir_path = os.path.dirname(cleaned) if os.path.splitext(cleaned)[1] else cleaned
    if not dir_path:
        dir_path = "."
    if not os.path.isdir(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except OSError:
            raise GhostbitMCPError(
                f"Cannot create output directory: {os.path.basename(dir_path)}"
            )
    if not os.access(dir_path, os.W_OK):
        raise GhostbitMCPError(f"Output directory is not writable: {dir_path}")
    return cleaned


# --- Filename Sanitization (Prompt Injection Defense) --- #


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename from decoded/extracted files before including in responses.

    4-pass sanitization pipeline for filenames:
    Pass 1 (Control chars): Strip control characters and non-printable chars
    Pass 2 (XSS): HTML entity escape to neutralize any markup
    Pass 3 (Path/Shell): Replace path separators and shell metacharacters
    Pass 4 (Prompt injection): Escape patterns that look like LLM instructions

    Also truncates to MAX_FILENAME_LENGTH.
    """
    # Pass 1: Strip control characters and non-printable characters
    cleaned = "".join(
        c
        for c in filename
        if unicodedata.category(c)[0] not in ("C",)  # Control characters
        and c.isprintable()
    )

    # Pass 2: XSS — HTML entity escape (neutralize <script>, &, ", etc.)
    cleaned = html.escape(cleaned, quote=True)

    # Pass 3: Path/Shell — replace separators and dangerous characters
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    for c in "|;&$`!><":
        cleaned = cleaned.replace(c, "_")

    # Truncate long names
    if len(cleaned) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(cleaned)
        if ext:
            cleaned = name[: MAX_FILENAME_LENGTH - len(ext) - 3] + "..." + ext
        else:
            cleaned = cleaned[:MAX_FILENAME_LENGTH] + "..."

    # Pass 4: Prompt injection — escape patterns that look like LLM instructions
    instruction_patterns = [
        r"^(SYSTEM|ADMIN|USER|ASSISTANT|HUMAN|EXECUTE|RUN|DELETE|SUDO)\s*:",  # With colon
        r"^(IGNORE|OVERRIDE)\s+",  # Without colon (e.g., "IGNORE previous instructions")
        r"^#+\s",  # Markdown headers
        r"^\[.*\]\(.*\)",  # Markdown links
        r"^```",  # Code blocks
    ]
    for pattern in instruction_patterns:
        if re.match(pattern, cleaned, re.IGNORECASE):
            cleaned = f"__{cleaned}"

    # If empty after sanitization, use a safe placeholder
    if not cleaned or cleaned.isspace():
        cleaned = "unnamed_file"

    return cleaned


# --- Quality Mapping --- #


def map_quality(quality_str: str) -> EncodeMode:
    """Map a quality string to an EncodeMode enum value.

    Args:
        quality_str: One of "low", "normal", "high" (case-insensitive).

    Returns:
        The corresponding EncodeMode.

    Raises:
        GhostbitMCPError if the quality string is invalid.
    """
    mode = QUALITY_MAP.get(quality_str.lower().strip())
    if mode is None:
        raise GhostbitMCPError(
            f"Invalid quality '{quality_str}'. Must be one of: low, normal, high"
        )
    return mode


# --- Secure Password Resolution --- #


def resolve_password(
    password_env: str | None = None,
    password_file: str | None = None,
) -> str | None:
    """Resolve a password from a secure source — never from plaintext tool params.

    The password value is NEVER visible to the LLM. The model only sees the
    environment variable name or file path, not the actual password.

    Resolution methods:
    - password_env: Name of an environment variable containing the password.
    - password_file: Path to a password file (auto-detects SOPS encryption).

    Returns the resolved password string, or None if no password source given.
    Raises GhostbitMCPError on resolution failure.
    """
    if password_env and password_file:
        raise GhostbitMCPError("Provide either password_env or password_file, not both")

    if password_env:
        return _resolve_from_env(password_env)

    if password_file:
        return _resolve_from_file(password_file)

    return None


def _resolve_from_env(env_var_name: str) -> str:
    """Read password from an environment variable.

    The LLM sees: password_env="GHOSTBIT_PASSWORD"
    The server reads: os.environ["GHOSTBIT_PASSWORD"] → actual password
    """
    # Validate env var name (prevent injection via malicious names)
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", env_var_name):
        raise GhostbitMCPError(
            f"Invalid environment variable name: '{env_var_name}'. "
            f"Must contain only letters, digits, and underscores."
        )

    value = os.environ.get(env_var_name)
    if value is None:
        raise GhostbitMCPError(
            f"Environment variable '{env_var_name}' is not set. "
            f"Set it before launching the MCP server."
        )
    if not value:
        raise GhostbitMCPError(f"Environment variable '{env_var_name}' is empty.")

    logger.info("Password resolved from environment variable: %s", env_var_name)
    return value


def _resolve_from_file(file_path: str) -> str:
    """Read password from a file, with SOPS auto-detection.

    Auto-detects SOPS-encrypted files and decrypts in memory.
    Falls back to reading as plaintext for non-SOPS files (e.g., chmod 600).

    The decrypted password is held only in memory, never written to disk.
    """
    cleaned = sanitize_input_path(file_path)
    validate_path_in_sandbox(cleaned, "Password file")

    if not os.path.exists(cleaned):
        raise GhostbitMCPError(f"Password file not found: {file_path}")
    if not os.path.isfile(cleaned):
        raise GhostbitMCPError(f"Password file is not a regular file: {file_path}")

    # Read file content to detect format
    try:
        with open(cleaned, "r") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        raise GhostbitMCPError(f"Cannot read password file: {file_path}")

    # Auto-detect SOPS encryption
    if _is_sops_encrypted(content):
        logger.info("SOPS-encrypted password file detected, decrypting in memory")
        return _decrypt_sops(cleaned)

    # Plaintext fallback — just read the content
    password = content.strip()
    if not password:
        raise GhostbitMCPError(f"Password file is empty: {file_path}")

    logger.info("Password resolved from plaintext file: %s", file_path)
    return password


def _is_sops_encrypted(content: str) -> bool:
    """Detect if file content is SOPS-encrypted.

    Checks for SOPS metadata markers in YAML and JSON formats.
    """
    # JSON format: look for "sops" key
    if content.strip().startswith("{"):
        return '"sops"' in content and '"version"' in content

    # YAML format: look for "sops:" key at start of line
    return bool(re.search(r"^sops:", content, re.MULTILINE))


def _decrypt_sops(file_path: str) -> str:
    """Decrypt a SOPS-encrypted file in memory.

    Uses the `sops` binary to decrypt. The decrypted content is held
    only in memory and never written to disk.

    Automatically sets SOPS_AGE_KEY_FILE to the standard default location
    (~/.config/sops/age/keys.txt) if not already set, so users don't need
    to configure env vars manually.

    Requires: `sops` binary available in PATH.
    """

    # Auto-detect age key file at standard location if not configured
    env = dict(os.environ)
    if "SOPS_AGE_KEY_FILE" not in env:
        default_key = os.path.expanduser("~/.config/sops/age/keys.txt")
        if os.path.exists(default_key):
            env["SOPS_AGE_KEY_FILE"] = default_key
            logger.info("Auto-detected age key at %s", default_key)

    try:
        result = subprocess.run(
            ["sops", "-d", "--output-type", "raw", file_path],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
    except FileNotFoundError:
        raise GhostbitMCPError(
            "SOPS binary not found. Install SOPS to use encrypted password files: "
            "https://github.com/getsops/sops"
        )
    except subprocess.TimeoutExpired:
        raise GhostbitMCPError("SOPS decryption timed out (30s)")

    if result.returncode != 0:
        # Don't leak SOPS error details — could contain key info
        logger.error("SOPS decryption failed: %s", result.stderr)
        raise GhostbitMCPError(
            "Failed to decrypt SOPS password file. "
            "Check that SOPS keys are configured correctly."
        )

    password = result.stdout.strip()
    if not password:
        raise GhostbitMCPError("SOPS decryption produced empty result")

    logger.info("Password decrypted from SOPS file: %s", file_path)
    return password


# --- Error Sanitization (Information Disclosure Prevention) --- #


def sanitize_error(exc: Exception) -> str:
    """Translate a domain exception into a safe, category-level error message.

    NEVER returns file contents, passwords, or full stack traces.
    Only returns: error category and safe metadata (no raw exception text
    in the generic fallback — that could leak passwords, paths, or internal state).
    """
    msg = str(exc)

    # Map known exception types to safe categories
    if "password" in msg.lower() or "decrypt" in msg.lower() or "key" in msg.lower():
        return "Decryption failed - incorrect password or corrupted data"
    if "capacity" in msg.lower() or "too large" in msg.lower():
        return "Capacity exceeded - secret files are too large for the carrier"
    if "not found" in msg.lower() or "no such file" in msg.lower():
        return "File not found - check the file path and try again"
    if "format" in msg.lower() or "unsupported" in msg.lower():
        return "Unsupported format - check supported formats via the format resources"
    if "permission" in msg.lower() or "access" in msg.lower():
        return "Permission denied - check file and directory permissions"
    if isinstance(exc, GhostbitMCPError):
        return msg

    # Generic fallback — NEVER include raw exception message, it could contain
    # passwords, file contents, internal paths, or library internals
    logger.error(
        "Unhandled exception in MCP tool: %s: %s",
        type(exc).__name__,
        msg,
        exc_info=True,
    )
    return "An unexpected error occurred. Check server logs for details."


# --- Audit Logging --- #


def scrub_params_for_logging(params: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of parameters with sensitive fields redacted.

    Passwords are replaced with '[REDACTED]'. All other fields are preserved.
    Used for structured audit logging of tool invocations.
    """
    scrubbed = dict(params)
    if "password" in scrubbed and scrubbed["password"] is not None:
        scrubbed["password"] = "[REDACTED]"
    return scrubbed
