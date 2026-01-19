# Changelog

## 0.1.1 - 2026-01-18

### Added

#### AudioStego
- Initial release of GH0STB1T, with audio steganography
- Multi-format audio steganography support (WAV, FLAC, MP3, M4A, AIFF/AIF)
- Password-protected encryption using AES-256-GCM with ARGON2ID key derivation (legacy AES-256-CBC support maintained)
- LSB (Least Significant Bit) steganography implementation
- Three quality modes: Low (2:1), Normal (4:1), High (8:1)
- Command-line interface with encode, decode, analyze, info, and test commands
- Support for hiding multiple files in a single carrier
- Interactive password prompts
- Verbose mode for detailed operation logs
- Automatic format conversion using pydub and soundfile
- Test file generation functionality
- Cross-platform compatibility (macOS, Linux)
- Docker containerization
- Support for LLM Skills
