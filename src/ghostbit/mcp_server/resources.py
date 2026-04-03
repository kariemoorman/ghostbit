import ghostbit
from ghostbit.audiostego.core.audio_multiformat_coder import AudioMultiFormatCoder
from ghostbit.audiostego.skills import (
    get_audio_llm_context,
    load_audio_skill,
    list_audio_skills,
)
from ghostbit.imagestego.core.image_multiformat_coder import ImageMultiFormatCoder
from ghostbit.imagestego.skills import (
    get_image_llm_context,
    load_image_skill,
    list_image_skills,
)
from ghostbit.mcp_server.server import mcp

# --- Version --- #


@mcp.resource("ghostbit://version")
def get_version() -> str:
    """Ghostbit MCP server version and capability summary."""
    audio_skills = list_audio_skills()
    image_skills = list_image_skills()

    return (
        f"ghostbit v{ghostbit.__version__}\n"
        f"Multi-format steganography toolkit\n"
        f"\n"
        f"Capabilities:\n"
        f"  Tools: 10 (audio: encode, decode, capacity, analyze, generate | "
        f"image: encode, decode, capacity, analyze, generate)\n"
        f"  Resources: 8 (version, formats, skill docs)\n"
        f"  Prompts: 6 (workflow templates)\n"
        f"\n"
        f"Encryption: AES-256-GCM with Argon2id KDF\n"
        f"Audio skills: {', '.join(audio_skills)}\n"
        f"Image skills: {', '.join(image_skills)}"
    )


# --- Audio Format Resources --- #


@mcp.resource("ghostbit://formats/audio/input")
def get_audio_input_formats() -> str:
    """Supported audio input formats for encoding, decoding, and analysis."""
    formats = AudioMultiFormatCoder.SUPPORTED_INPUT_FORMATS
    return "Supported audio input formats:\n" + "\n".join(
        f"  - {fmt}" for fmt in sorted(formats)
    )


@mcp.resource("ghostbit://formats/audio/output")
def get_audio_output_formats() -> str:
    """Supported audio output formats for encoding."""
    formats = AudioMultiFormatCoder.SUPPORTED_OUTPUT_FORMATS
    return "Supported audio output formats:\n" + "\n".join(
        f"  - {fmt}" for fmt in sorted(formats)
    )


# --- Image Format Resource --- #


@mcp.resource("ghostbit://formats/image")
def get_image_formats() -> str:
    """Supported image formats with their steganography algorithms."""
    fmt_algos = ImageMultiFormatCoder.FORMAT_ALGORITHMS
    lines = ["Supported image formats and algorithms:"]
    for fmt, algo in sorted(fmt_algos.items()):
        lines.append(f"  - {fmt}: {algo.name}")
    return "\n".join(lines)


# --- Audio Skill Resources --- #


@mcp.resource("ghostbit://skills/audio")
def get_all_audio_skills() -> str:
    """Complete audio steganography documentation (all skills combined)."""
    return get_audio_llm_context()


@mcp.resource("ghostbit://skills/audio/{skill_name}")
def get_audio_skill(skill_name: str) -> str:
    """Individual audio steganography skill document.

    Available skills: steganography, capacity, troubleshooting
    """
    try:
        skill = load_audio_skill(skill_name)
        return skill.content
    except ValueError as e:
        return f"Error: {e}"


# --- Image Skill Resources --- #


@mcp.resource("ghostbit://skills/image")
def get_all_image_skills() -> str:
    """Complete image steganography documentation (all skills combined)."""
    return get_image_llm_context()


@mcp.resource("ghostbit://skills/image/{skill_name}")
def get_image_skill(skill_name: str) -> str:
    """Individual image steganography skill document.

    Available skills: steganography, capacity, troubleshooting
    """
    try:
        skill = load_image_skill(skill_name)
        return skill.content
    except ValueError as e:
        return f"Error: {e}"
