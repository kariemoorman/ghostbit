import logging
import os
import svgwrite
from PIL import Image

from ghostbit.imagestego.core.image_multiformat_coder import (
    ImageGenerator,
    ImageMultiFormatCoder,
    ImageMultiFormatCoderException,
)
from ghostbit.imagestego.core.image_steganography import ImageSteganographyException
from ghostbit.mcp_server.errors import (
    IMAGE_EXTENSIONS,
    GhostbitMCPError,
    capture_stdout,
    resolve_password,
    sanitize_error,
    sanitize_filename,
    validate_directory_writable,
    validate_file_exists,
    validate_file_extension,
    validate_file_size,
)
from ghostbit.mcp_server.server import mcp

logger = logging.getLogger("ghostbit.mcp_server.image")


# --- Image Encode --- #


@mcp.tool()
def image_encode(
    input_path: str,
    secret_file_paths: list[str],
    output_path: str,
    password_env: str | None = None,
    password_file: str | None = None,
) -> str:
    """Hide secret files inside an image carrier using steganography.

    Embeds one or more secret files into a cover image. The algorithm is
    selected automatically based on the image format (LSB for most formats,
    Palette for GIF, SVG XML embedding for SVG). Optionally encrypts with
    AES-256-GCM and Argon2id key derivation.

    SECURITY: Passwords are resolved server-side from environment variables
    or encrypted files — never passed as plaintext through the AI model.
    Set the password in an env var before launching the MCP client:
        export GHOSTBIT_PASSWORD="your_password"
    Then pass password_env="GHOSTBIT_PASSWORD" to this tool.

    Risk level: WRITE (reads secret files, writes output image)

    Args:
        input_path: Path to the cover image (PNG, BMP, TIFF, JPEG, GIF, WEBP, SVG, etc.)
        secret_file_paths: List of file paths to hide inside the image
        output_path: Directory where the output stego image will be saved
        password_env: Name of environment variable containing the encryption password
        password_file: Path to a password file (supports SOPS-encrypted files)
    """
    logger.info(
        "image_encode invoked: %s",
        {
            "input_path": input_path,
            "secret_file_paths": secret_file_paths,
            "output_path": output_path,
            "password_env": password_env,
            "password_file": "(set)" if password_file else None,
        },
    )

    try:
        password = resolve_password(
            password_env=password_env, password_file=password_file
        )

        validate_file_exists(input_path, "Cover image")
        validate_file_extension(input_path, IMAGE_EXTENSIONS, "Cover image")
        validate_file_size(input_path, label="Cover image")

        if not secret_file_paths:
            raise GhostbitMCPError("At least one secret file path is required")
        for sf in secret_file_paths:
            validate_file_exists(sf, "Secret file")
            validate_file_size(sf, label="Secret file")

        validate_directory_writable(output_path)

        coder = ImageMultiFormatCoder()
        with capture_stdout():
            result_path = coder.encode(
                cover_path=input_path,
                secret_files=secret_file_paths,
                output_dir=output_path,
                password=password,
            )

        # Return structured metadata only
        if result_path and os.path.exists(result_path):
            output_size = os.path.getsize(result_path)
            output_size_mb = output_size / (1024 * 1024)
            return (
                f"Encoding successful.\n"
                f"Output: {result_path} ({output_size_mb:.2f} MB)\n"
                f"Secret files encoded: {len(secret_file_paths)}\n"
                f"Encrypted: {'yes' if password else 'no'}"
            )
        else:
            return (
                f"Encoding completed.\n"
                f"Output directory: {output_path}\n"
                f"Secret files encoded: {len(secret_file_paths)}\n"
                f"Encrypted: {'yes' if password else 'no'}"
            )

    except GhostbitMCPError as e:
        return f"Error: {e}"
    except (ImageMultiFormatCoderException, ImageSteganographyException) as e:
        return f"Error: {sanitize_error(e)}"
    except Exception as e:
        return f"Error: {sanitize_error(e)}"


# --- Image Decode --- #


@mcp.tool()
def image_decode(
    input_path: str,
    output_dir: str,
    password_env: str | None = None,
    password_file: str | None = None,
) -> str:
    """Extract hidden files from a stego image.

    Reverses the steganography encoding to recover secret files from an image.
    If the files were encrypted, the correct password is required.

    SECURITY: Passwords are resolved server-side — never passed as plaintext.
    Extracted file contents are NEVER returned — only filenames and sizes.

    Risk level: WRITE (writes extracted files to output_dir)

    Args:
        input_path: Path to the stego image containing hidden data
        output_dir: Directory where extracted files will be saved
        password_env: Name of environment variable containing the decryption password
        password_file: Path to a password file (supports SOPS-encrypted files)
    """
    logger.info(
        "image_decode invoked: %s",
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

        validate_file_exists(input_path, "Stego image")
        validate_file_extension(input_path, IMAGE_EXTENSIONS, "Stego image")
        validate_file_size(input_path, label="Stego image")
        validate_directory_writable(output_dir)

        coder = ImageMultiFormatCoder()
        with capture_stdout():
            count = coder.decode(
                stego_path=input_path,
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
                f"Decoding completed (reported {count} files) but no files found in {output_dir}. "
                f"The image may not contain hidden data, or the password may be incorrect."
            )

    except GhostbitMCPError as e:
        return f"Error: {e}"
    except (ImageMultiFormatCoderException, ImageSteganographyException) as e:
        return f"Error: {sanitize_error(e)}"
    except Exception as e:
        return f"Error: {sanitize_error(e)}"


# --- Image Capacity --- #


@mcp.tool()
def image_capacity(input_path: str) -> str:
    """Check how much secret data an image can hide.

    Calculates the steganographic capacity of an image file. The algorithm
    is auto-detected from the image format (LSB, Palette, SVG XML).

    Risk level: READ-ONLY (reads file metadata, no writes)

    Args:
        input_path: Path to the image file
    """
    logger.info("image_capacity invoked: %s", {"input_path": input_path})

    try:
        validate_file_exists(input_path, "Image file")
        validate_file_extension(input_path, IMAGE_EXTENSIONS, "Image file")
        validate_file_size(input_path, label="Image file")

        coder = ImageMultiFormatCoder()
        with capture_stdout():
            result = coder.calculate_capacity(image_path=input_path)

        return (
            f"Image: {input_path}\n"
            f"Format: {result['format']}\n"
            f"Algorithm: {result['algorithm']}\n"
            f"Capacity: {result['capacity_bytes']:,} bytes "
            f"({result['capacity_kb']:.2f} KB / {result['capacity_mb']:.2f} MB)"
        )

    except GhostbitMCPError as e:
        return f"Error: {e}"
    except (ImageMultiFormatCoderException, ImageSteganographyException) as e:
        return f"Error: {sanitize_error(e)}"
    except Exception as e:
        return f"Error: {sanitize_error(e)}"


# --- Image Analyze --- #


@mcp.tool()
def image_analyze(
    input_path: str,
    password_env: str | None = None,
    password_file: str | None = None,
) -> str:
    """Detect whether an image contains hidden steganographic data.

    Analyzes an image for signs of embedded data. Reports the format,
    algorithm, and whether encryption was detected.

    SECURITY: Passwords are resolved server-side — never passed as plaintext.

    Risk level: READ-ONLY (reads file metadata, no writes)

    Args:
        input_path: Path to the image file to analyze
        password_env: Name of environment variable containing the password
        password_file: Path to a password file (supports SOPS-encrypted files)
    """
    logger.info(
        "image_analyze invoked: %s",
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

        validate_file_exists(input_path, "Image file")
        validate_file_extension(input_path, IMAGE_EXTENSIONS, "Image file")
        validate_file_size(input_path, label="Image file")

        coder = ImageMultiFormatCoder()
        with capture_stdout():
            result = coder.analyze(image_path=input_path)

        file_size = os.path.getsize(input_path)
        file_size_mb = file_size / (1024 * 1024)

        lines = [
            f"File: {input_path} ({file_size_mb:.2f} MB)",
            f"Format: {result.get('format', 'unknown')}",
            f"Hidden data detected: {'yes' if result.get('has_hidden_data') else 'no'}",
        ]
        if result.get("algorithm") is not None:
            lines.append(f"Algorithm: {result['algorithm']}")
        if result.get("encrypted") is not None:
            lines.append(f"Encrypted: {'yes' if result['encrypted'] else 'no'}")

        return "\n".join(lines)

    except GhostbitMCPError as e:
        return f"Error: {e}"
    except (ImageMultiFormatCoderException, ImageSteganographyException) as e:
        return f"Error: {sanitize_error(e)}"
    except Exception as e:
        return f"Error: {sanitize_error(e)}"


# --- Generate Image Carrier --- #

# Supported output formats for the generator
_GENERATOR_FORMATS = {
    ".png",
    ".bmp",
    ".tiff",
    ".tif",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
}
_PATTERN_TYPES = {"noise", "gradient", "channels", "waves", "random"}


@mcp.tool()
def generate_image_carrier(
    output_path: str,
    width: int = 800,
    height: int = 600,
    pattern: str = "random",
) -> str:
    """Create a carrier image for steganography with procedural patterns.

    Generates an image file that can be used as a carrier for hiding
    secret files. Useful when no existing image is available.

    Risk level: WRITE (creates a new file at output_path)

    Args:
        output_path: Where to save the generated image (extension determines format: .png, .bmp, .jpg, .tiff, .webp, .gif, .svg)
        width: Image width in pixels (default: 800)
        height: Image height in pixels (default: 600)
        pattern: Visual pattern - "noise", "gradient", "channels", "waves", or "random" (default: "random")
    """
    logger.info(
        "generate_image_carrier invoked: %s",
        {
            "output_path": output_path,
            "width": width,
            "height": height,
            "pattern": pattern,
        },
    )

    try:
        validate_file_extension(output_path, _GENERATOR_FORMATS, "Output file")
        validate_directory_writable(output_path)

        if width <= 0 or width > 10000:
            raise GhostbitMCPError("Width must be between 1 and 10000 pixels")
        if height <= 0 or height > 10000:
            raise GhostbitMCPError("Height must be between 1 and 10000 pixels")
        if pattern not in _PATTERN_TYPES:
            raise GhostbitMCPError(
                f"Invalid pattern '{pattern}'. Must be one of: {', '.join(sorted(_PATTERN_TYPES))}"
            )

        ext = os.path.splitext(output_path)[1].lower()
        out_dir = os.path.dirname(output_path) or "."

        # Use the existing ImageGenerator class
        generator = ImageGenerator(out_dir=out_dir, width=width, height=height)

        with capture_stdout():
            if ext == ".svg":

                # Generate SVG using the generator's pattern
                dwg = svgwrite.Drawing(
                    output_path, size=(width, height), profile="full"
                )
                c1 = generator.rng.integers(0, 256, size=3)
                c2 = generator.rng.integers(0, 256, size=3)
                c3 = generator.rng.integers(0, 256, size=3)
                gradient = dwg.linearGradient(
                    start=(0, 0), end=(1, 1), id="rgbGradient"
                )
                gradient.add_stop_color(0.0, f"rgb({c1[0]},{c1[1]},{c1[2]})")
                gradient.add_stop_color(0.5, f"rgb({c2[0]},{c2[1]},{c2[2]})")
                gradient.add_stop_color(1.0, f"rgb({c3[0]},{c3[1]},{c3[2]})")
                dwg.defs.add(gradient)
                dwg.add(
                    dwg.rect(
                        insert=(0, 0), size=("100%", "100%"), fill="url(#rgbGradient)"
                    )
                )
                dwg.save()
            elif ext == ".gif":
                # Generate a static GIF with palette
                design = (
                    pattern
                    if pattern != "random"
                    else generator.rng.choice(
                        ["noise", "gradient", "channels", "waves"]
                    )
                )
                rgb = generator.generate_pattern(design)
                img = generator.strip_metadata(Image.fromarray(rgb, "RGB"))
                palette_img = Image.new("P", (1, 1))
                palette_img.putpalette(generator.fixed_rgb_palette())
                gif = img.quantize(palette=palette_img, dither=Image.Dither.NONE)
                gif.save(output_path, optimize=False)
            else:
                # Generate RGB image and save in requested format
                design = (
                    pattern
                    if pattern != "random"
                    else generator.rng.choice(
                        ["noise", "gradient", "channels", "waves"]
                    )
                )
                rgb = generator.generate_pattern(design)
                img = generator.strip_metadata(Image.fromarray(rgb, "RGB"))

                save_kwargs: dict = {}
                if ext in (".jpg", ".jpeg"):
                    save_kwargs = {"quality": 95, "subsampling": 0}
                elif ext == ".png":
                    save_kwargs = {"compress_level": 9}
                elif ext in (".tiff", ".tif"):
                    save_kwargs = {"compression": "raw"}
                elif ext == ".webp":
                    save_kwargs = {"format": "WEBP", "lossless": True, "quality": 100}

                img.save(output_path, **save_kwargs)

        output_size = os.path.getsize(output_path)
        output_size_mb = output_size / (1024 * 1024)

        return (
            f"Image carrier generated.\n"
            f"Output: {output_path} ({output_size_mb:.2f} MB)\n"
            f"Dimensions: {width}x{height}\n"
            f"Pattern: {pattern}\n"
            f"Format: {ext.lstrip('.')}"
        )

    except GhostbitMCPError:
        raise
    except Exception as e:
        raise GhostbitMCPError(sanitize_error(e))
