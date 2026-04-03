import ghostbit
from mcp.server.fastmcp import FastMCP

# --- Server Instance --- #

mcp = FastMCP(
    "ghostbit",
    instructions=(
        f"ghostbit v{ghostbit.__version__} - "
        "Multi-format steganography toolkit. Hide files in audio and images "
        "with AES-256-GCM encryption and Argon2id key derivation."
    ),
)

# --- Register tools, resources, and prompts --- #
# Importing these modules triggers @mcp.tool()/@mcp.resource()/@mcp.prompt() registration

import ghostbit.mcp_server.tools.audio_tools  # noqa: F401, E402
import ghostbit.mcp_server.tools.image_tools  # noqa: F401, E402
import ghostbit.mcp_server.resources  # noqa: F401, E402
import ghostbit.mcp_server.prompts  # noqa: F401, E402

# --- Entry Point --- #


def main() -> None:
    """Run the ghostbit MCP server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
