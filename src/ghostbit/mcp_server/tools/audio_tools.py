import logging
import math
import os
import struct
import wave

from ghostbit.audiostego.core.audio_multiformat_coder import (
    AudioMultiFormatCoder,
    AudioMultiFormatCoderException,
)
from ghostbit.audiostego.core.audio_steganography import (
    AudioSteganographyException,
    KeyRequiredEventArgs,
)
from ghostbit.mcp_server.errors import (
    AUDIO_INPUT_EXTENSIONS,
    AUDIO_OUTPUT_EXTENSIONS,
    GhostbitMCPError,
    capture_stdout,
    map_quality,
    resolve_password,
    sanitize_error,
    sanitize_filename,
    validate_directory_writable,
    validate_file_exists,
    validate_file_extension,
    validate_file_size,
)
from ghostbit.mcp_server.server import mcp

logger = logging.getLogger("ghostbit.mcp_server.audio")


# --- Audio Encode --- #


@mcp.tool()
def audio_encode(
    input_path: str,
    secret_file_paths: list[str],
    output_path: str,
    quality: str = "normal",
    password_env: str | None = None,
    password_file: str | None = None,
) -> str:
    """Hide secret files inside an audio carrier file using steganography.

    Embeds one or more secret files into an audio carrier using LSB (Least
    Significant Bit) steganography. Optionally encrypts with AES-256-GCM
    and Argon2id key derivation.

    SECURITY: Passwords are resolved server-side from environment variables
    or encrypted files — never passed as plaintext through the AI model.
    Set the password in an env var before launching the MCP client:
        export GHOSTBIT_PASSWORD="your_password"
    Then pass password_env="GHOSTBIT_PASSWORD" to this tool.

    Risk level: WRITE (reads secret files, writes output file)

    Args:
        input_path: Path to the carrier audio file (WAV, FLAC, MP3, M4A, AIFF)
        secret_file_paths: List of file paths to hide inside the carrier
        output_path: Where to write the output audio file (WAV, FLAC, M4A, AIFF)
        quality: Encoding quality - "low" (more capacity), "normal", or "high" (less capacity, better audio)
        password_env: Name of environment variable containing the encryption password
        password_file: Path to a password file (supports SOPS-encrypted files)
    """
    logger.info(
        "audio_encode invoked: %s",
        {
            "input_path": input_path,
            "secret_file_paths": secret_file_paths,
            "output_path": output_path,
            "quality": quality,
            "password_env": password_env,
            "password_file": "(set)" if password_file else None,
        },
    )

    try:
        # Resolve password from secure source (never from plaintext param)
        password = resolve_password(
            password_env=password_env, password_file=password_file
        )

        # Validate inputs
        validate_file_exists(input_path, "Carrier file")
        validate_file_extension(input_path, AUDIO_INPUT_EXTENSIONS, "Carrier file")
        validate_file_size(input_path, label="Carrier file")

        if not secret_file_paths:
            raise GhostbitMCPError("At least one secret file path is required")
        for sf in secret_file_paths:
            validate_file_exists(sf, "Secret file")
            validate_file_size(sf, label="Secret file")

        validate_file_extension(output_path, AUDIO_OUTPUT_EXTENSIONS, "Output file")
        validate_directory_writable(output_path)

        encode_mode = map_quality(quality)

        # Execute with stdout capture (protocol integrity)
        coder = AudioMultiFormatCoder()
        with capture_stdout():
            coder.encode_files_multi_format(
                carrier_file=input_path,
                secret_files=secret_file_paths,
                output_file=output_path,
                password=password,
                quality_mode=encode_mode,
            )

        # Return structured metadata only — never file contents
        output_size = os.path.getsize(output_path)
        output_size_mb = output_size / (1024 * 1024)
        return (
            f"Encoding successful.\n"
            f"Output: {output_path} ({output_size_mb:.2f} MB)\n"
            f"Secret files encoded: {len(secret_file_paths)}\n"
            f"Quality: {quality}\n"
            f"Encrypted: {'yes' if password else 'no'}"
        )

    except GhostbitMCPError as e:
        return f"Error: {e}"
    except (AudioMultiFormatCoderException, AudioSteganographyException) as e:
        return f"Error: {sanitize_error(e)}"
    except Exception as e:
        return f"Error: {sanitize_error(e)}"


# --- Audio Decode --- #


@mcp.tool()
def audio_decode(
    input_path: str,
    output_dir: str,
    password_env: str | None = None,
    password_file: str | None = None,
) -> str:
    """Extract hidden files from an encoded audio file.

    Reverses the steganography encoding process to recover secret files.
    If the files were encrypted, the correct password is required.

    SECURITY: Passwords are resolved server-side from environment variables
    or encrypted files — never passed as plaintext. Extracted file contents
    are NEVER returned — only filenames and sizes.

    Risk level: WRITE (writes extracted files to output_dir)

    Args:
        input_path: Path to the encoded audio file containing hidden data
        output_dir: Directory where extracted files will be saved
        password_env: Name of environment variable containing the decryption password
        password_file: Path to a password file (supports SOPS-encrypted files)
    """
    logger.info(
        "audio_decode invoked: %s",
        {
            "input_path": input_path,
            "output_dir": output_dir,
            "password_env": password_env,
            "password_file": "(set)" if password_file else None,
        },
    )

    try:
        password = resolve_password(
            password_env=password_env, password_file=password_file
        )

        validate_file_exists(input_path, "Encoded file")
        validate_file_extension(input_path, AUDIO_INPUT_EXTENSIONS, "Encoded file")
        validate_file_size(input_path, label="Encoded file")
        validate_directory_writable(output_dir)

        coder = AudioMultiFormatCoder()

        # Set up the key callback — required because analyze_wav re-derives
        # the key using the salt from the WAV header. Without this callback,
        # the password is lost and decryption fails silently.
        if password:

            def _supply_password(args: KeyRequiredEventArgs) -> None:
                args.key = password

            coder.on_key_required = _supply_password

        with capture_stdout():
            coder.decode_files_multi_format(
                encoded_file=input_path,
                output_dir=output_dir,
                password=password,
            )

        # List extracted files — sanitized metadata only (never file contents)
        extracted = []
        if os.path.isdir(output_dir):
            for f in os.listdir(output_dir):
                fpath = os.path.join(output_dir, f)
                if os.path.isfile(fpath):
                    size = os.path.getsize(fpath)
                    safe_name = sanitize_filename(f)
                    extracted.append(f"{safe_name} ({size:,} bytes)")

        if extracted:
            file_list = "\n".join(f"  - {f}" for f in extracted)
            return (
                f"Decoding successful.\n"
                f"Output directory: {output_dir}\n"
                f"Files extracted: {len(extracted)}\n{file_list}"
            )
        else:
            return (
                f"Decoding completed but no files were found in {output_dir}. "
                f"The audio file may not contain hidden data, or the password may be incorrect."
            )

    except GhostbitMCPError as e:
        return f"Error: {e}"
    except (AudioMultiFormatCoderException, AudioSteganographyException) as e:
        return f"Error: {sanitize_error(e)}"
    except Exception as e:
        return f"Error: {sanitize_error(e)}"


# --- Audio Capacity --- #


@mcp.tool()
def audio_capacity(
    input_path: str,
    quality: str = "normal",
) -> str:
    """Check how much secret data an audio file can hide.

    Calculates the steganographic capacity of a carrier audio file
    at the specified quality level.

    Risk level: READ-ONLY (reads file metadata, no writes)

    Args:
        input_path: Path to the carrier audio file
        quality: Quality mode - "low" (more capacity), "normal", or "high" (less capacity)
    """
    logger.info(
        "audio_capacity invoked: %s",
        {"input_path": input_path, "quality": quality},
    )

    try:
        validate_file_exists(input_path, "Carrier file")
        validate_file_extension(input_path, AUDIO_INPUT_EXTENSIONS, "Carrier file")
        validate_file_size(input_path, label="Carrier file")

        encode_mode = map_quality(quality)

        coder = AudioMultiFormatCoder()
        with capture_stdout():
            capacity_bytes = coder.calculate_capacity(
                audio_file=input_path,
                quality_mode=encode_mode,
            )

        capacity_kb = capacity_bytes / 1024
        capacity_mb = capacity_bytes / (1024 * 1024)

        return (
            f"Carrier: {input_path}\n"
            f"Quality: {quality}\n"
            f"Capacity: {capacity_bytes:,} bytes ({capacity_kb:.2f} KB / {capacity_mb:.2f} MB)"
        )

    except GhostbitMCPError as e:
        return f"Error: {e}"
    except (AudioMultiFormatCoderException, AudioSteganographyException) as e:
        return f"Error: {sanitize_error(e)}"
    except Exception as e:
        return f"Error: {sanitize_error(e)}"


# --- Audio Analyze --- #


@mcp.tool()
def audio_analyze(
    input_path: str,
    password_env: str | None = None,
    password_file: str | None = None,
) -> str:
    """Detect whether an audio file contains hidden steganographic data.

    Analyzes an audio file for signs of embedded data. If a password is
    provided via env var or file, attempts to decrypt and list hidden files.

    SECURITY: Passwords are resolved server-side — never passed as plaintext.

    Risk level: READ-ONLY (reads file metadata, no writes)

    Args:
        input_path: Path to the audio file to analyze
        password_env: Name of environment variable containing the password
        password_file: Path to a password file (supports SOPS-encrypted files)
    """
    logger.info(
        "audio_analyze invoked: %s",
        {
            "input_path": input_path,
            "password_env": password_env,
            "password_file": "(set)" if password_file else None,
        },
    )

    try:
        password = resolve_password(
            password_env=password_env, password_file=password_file
        )

        validate_file_exists(input_path, "Audio file")
        validate_file_extension(input_path, AUDIO_INPUT_EXTENSIONS, "Audio file")
        validate_file_size(input_path, label="Audio file")

        coder = AudioMultiFormatCoder()

        if password:

            def _supply_password(args: KeyRequiredEventArgs) -> None:
                args.key = password

            coder.on_key_required = _supply_password

        with capture_stdout():
            has_hidden_data = coder.analyze_multi_format(
                audio_file=input_path,
                password=password,
            )

        file_size = os.path.getsize(input_path)
        file_size_mb = file_size / (1024 * 1024)

        return (
            f"File: {input_path} ({file_size_mb:.2f} MB)\n"
            f"Hidden data detected: {'yes' if has_hidden_data else 'no'}"
        )

    except GhostbitMCPError as e:
        return f"Error: {e}"
    except (AudioMultiFormatCoderException, AudioSteganographyException) as e:
        return f"Error: {sanitize_error(e)}"
    except Exception as e:
        return f"Error: {sanitize_error(e)}"


# --- Generate Audio Carrier --- #


@mcp.tool()
def generate_audio_carrier(
    output_path: str,
    duration: float = 5.0,
    frequency: float = 440.0,
    sample_rate: int = 44100,
    channels: int = 1,
) -> str:
    """Create a carrier WAV audio file for steganography.

    Generates a sine-wave WAV file that can be used as a carrier for
    hiding secret files. Useful when no existing audio file is available.

    Risk level: WRITE (creates a new file at output_path)

    Args:
        output_path: Where to save the generated WAV file
        duration: Duration in seconds (default: 5.0)
        frequency: Sine wave frequency in Hz (default: 440.0, concert A)
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of audio channels (default: 1 for mono)
    """
    logger.info(
        "generate_audio_carrier invoked: %s",
        {
            "output_path": output_path,
            "duration": duration,
            "frequency": frequency,
            "sample_rate": sample_rate,
            "channels": channels,
        },
    )

    try:
        validate_file_extension(output_path, {".wav"}, "Output file")
        validate_directory_writable(output_path)

        if duration <= 0 or duration > 300:
            raise GhostbitMCPError("Duration must be between 0 and 300 seconds")
        if frequency <= 0 or frequency > 22050:
            raise GhostbitMCPError("Frequency must be between 0 and 22050 Hz")
        if sample_rate not in (8000, 11025, 22050, 44100, 48000, 96000):
            raise GhostbitMCPError(
                "Sample rate must be one of: 8000, 11025, 22050, 44100, 48000, 96000"
            )
        if channels not in (1, 2):
            raise GhostbitMCPError("Channels must be 1 (mono) or 2 (stereo)")

        # Generate sine wave WAV — stdlib only, no pydub
        num_frames = int(sample_rate * duration)
        with wave.open(output_path, "w") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)

            for i in range(num_frames):
                value = int(
                    32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate)
                )
                sample = struct.pack("<h", value)
                # Write sample for each channel
                wav.writeframes(sample * channels)

        output_size = os.path.getsize(output_path)
        output_size_mb = output_size / (1024 * 1024)

        return (
            f"Audio carrier generated.\n"
            f"Output: {output_path} ({output_size_mb:.2f} MB)\n"
            f"Duration: {duration}s | Frequency: {frequency} Hz\n"
            f"Sample rate: {sample_rate} Hz | Channels: {channels}\n"
            f"Format: 16-bit PCM WAV"
        )

    except GhostbitMCPError:
        raise
    except Exception as e:
        raise GhostbitMCPError(sanitize_error(e))
