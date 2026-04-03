from mcp.server.fastmcp.prompts import base

from ghostbit.mcp_server.server import mcp

"""MCP prompt templates for common steganography workflows.

Prompts:
- hide_file_in_audio — guided audio encoding workflow
- hide_file_in_image — guided image encoding workflow
- extract_hidden_data — guided extraction workflow
- analyze_for_steganography — forensic analysis workflow
- check_capacity — capacity planning across quality modes
- quick_hide — end-to-end: generate carrier, encode, verify

SECURITY: Password values are NEVER embedded in prompt text. Prompts
indicate whether encryption is requested, but the actual password is
passed directly to the tool call — not through the prompt message.
This minimizes password exposure in conversation history and logs.
"""


def _password_instruction(use_encryption: bool = False) -> str:
    """Generate a safe password instruction for prompt text.

    Never includes any password value. Guides the model to use
    password_env or password_file for secure password resolution.
    """
    if use_encryption:
        return (
            "Use encryption. Pass password_env='GHOSTBIT_PASSWORD' to the tool "
            "(the user should have set this environment variable before launching). "
            "Do NOT ask the user to type their password in chat."
        )
    return "No encryption requested. Consider recommending encryption for security."


@mcp.prompt()
def hide_file_in_audio(
    carrier_path: str,
    secret_path: str,
    output_path: str,
    use_encryption: bool = False,
) -> list[base.Message]:
    """Guide the complete workflow for hiding a file inside an audio carrier.

    Steps: check capacity, encode secret file, verify output.
    """
    return [
        base.UserMessage(
            content=(
                f"I want to hide a file in an audio carrier. Please help me through this process:\n\n"
                f"1. First, check the capacity of the carrier file at: {carrier_path}\n"
                f"   - Check capacity for all three quality modes (low, normal, high)\n"
                f"2. Verify the secret file at: {secret_path} will fit in the carrier\n"
                f"3. Encode the secret file into the carrier, saving to: {output_path}\n"
                f"   - {_password_instruction(use_encryption)}\n"
                f"4. After encoding, analyze the output to confirm the data was hidden successfully"
            )
        )
    ]


@mcp.prompt()
def hide_file_in_image(
    cover_path: str,
    secret_path: str,
    output_path: str,
    use_encryption: bool = False,
) -> list[base.Message]:
    """Guide the complete workflow for hiding a file inside an image carrier.

    Steps: check capacity, encode secret file, verify output.
    """
    return [
        base.UserMessage(
            content=(
                f"I want to hide a file in an image. Please help me through this process:\n\n"
                f"1. First, check the capacity of the cover image at: {cover_path}\n"
                f"2. Verify the secret file at: {secret_path} will fit\n"
                f"3. Encode the secret file into the image, saving to: {output_path}\n"
                f"   - {_password_instruction(use_encryption)}\n"
                f"4. After encoding, analyze the output to confirm the data was hidden successfully"
            )
        )
    ]


@mcp.prompt()
def extract_hidden_data(
    file_path: str,
    output_dir: str,
    use_encryption: bool = False,
) -> list[base.Message]:
    """Guide the workflow for extracting hidden data from a file.

    Steps: analyze the file first, then decode.
    """
    password_note = (
        "The file is encrypted. Pass password_env='GHOSTBIT_PASSWORD' to the decode tool."
        if use_encryption
        else "No encryption indicated. If the file is encrypted, decryption will fail without a password."
    )
    return [
        base.UserMessage(
            content=(
                f"I want to extract hidden data from a file. Please help me:\n\n"
                f"1. First, analyze the file at: {file_path}\n"
                f"   - Determine if it's an audio or image file based on its extension\n"
                f"   - Check if it contains hidden data\n"
                f"2. If hidden data is detected, decode/extract to: {output_dir}\n"
                f"   - {password_note}\n"
                f"3. List the extracted files with their sizes"
            )
        )
    ]


@mcp.prompt()
def analyze_for_steganography(
    file_path: str,
    use_encryption: bool = False,
) -> list[base.Message]:
    """Perform forensic analysis of a file for hidden steganographic content."""
    return [
        base.UserMessage(
            content=(
                f"Perform a forensic steganography analysis on the file at: {file_path}\n\n"
                f"1. Determine the file type (audio or image) from its extension\n"
                f"2. Run the appropriate analyze tool\n"
                f"3. Check the capacity of the file\n"
                f"4. Report:\n"
                f"   - Whether hidden data was detected\n"
                f"   - The file format and steganography algorithm used\n"
                f"   - Whether encryption was detected\n"
                f"   - The total steganographic capacity of the file"
            )
        )
    ]


@mcp.prompt()
def check_capacity(carrier_path: str) -> list[base.Message]:
    """Plan steganographic capacity across all quality modes.

    Checks capacity at low, normal, and high quality for audio files,
    or reports the single capacity value for image files.
    """
    return [
        base.UserMessage(
            content=(
                f"Check the steganographic capacity of the carrier file at: {carrier_path}\n\n"
                f"1. Determine if it's an audio or image file from its extension\n"
                f"2. For audio files:\n"
                f"   - Check capacity at LOW quality (maximum capacity, lower audio quality)\n"
                f"   - Check capacity at NORMAL quality (balanced)\n"
                f"   - Check capacity at HIGH quality (minimum capacity, best audio quality)\n"
                f"   - Present a comparison table\n"
                f"3. For image files:\n"
                f"   - Check capacity (algorithm is auto-detected from format)\n"
                f"4. Recommend the best quality setting based on typical use cases"
            )
        )
    ]


@mcp.prompt()
def quick_hide(
    secret_path: str,
    media_type: str = "audio",
    output_dir: str = ".",
    use_encryption: bool = False,
) -> list[base.Message]:
    """End-to-end workflow: generate a carrier, encode a secret file, and verify.

    Uses generator tools to create a carrier on the fly, so no existing
    media file is needed.
    """
    if media_type.lower() == "image":
        return [
            base.UserMessage(
                content=(
                    f"I want to quickly hide a file with no existing carrier. Please:\n\n"
                    f"1. Generate a carrier image using generate_image_carrier\n"
                    f"   - Save to: {output_dir}/carrier.png\n"
                    f"   - Use a 'gradient' pattern at 800x600\n"
                    f"2. Check the capacity of the generated carrier\n"
                    f"3. Verify the secret file at: {secret_path} will fit\n"
                    f"4. Encode the secret file into the carrier\n"
                    f"   - Save output to: {output_dir}\n"
                    f"   - {_password_instruction(use_encryption)}\n"
                    f"5. Analyze the output to confirm success"
                )
            )
        ]
    else:
        return [
            base.UserMessage(
                content=(
                    f"I want to quickly hide a file with no existing carrier. Please:\n\n"
                    f"1. Generate a carrier WAV file using generate_audio_carrier\n"
                    f"   - Save to: {output_dir}/carrier.wav\n"
                    f"   - Use default settings (5 seconds, 440 Hz, 44100 sample rate)\n"
                    f"2. Check the capacity at all quality modes (low, normal, high)\n"
                    f"3. Verify the secret file at: {secret_path} will fit\n"
                    f"4. Encode the secret file into the carrier\n"
                    f"   - Save output to: {output_dir}/encoded.wav\n"
                    f"   - {_password_instruction(use_encryption)}\n"
                    f"5. Analyze the output to confirm success"
                )
            )
        ]
