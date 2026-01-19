# Audio Steganography with GH0STB1T

Complete guide for hiding data in audio files using the GH0STB1T: AUD10STEG0 Python package.

## Overview

GH0STB1T: AUD10STEG0 allows you to hide secret files inside audio carriers using LSB (Least Significant Bit) steganography. The data is embedded in the audio samples in a way that's imperceptible to human hearing.

## Installation

```bash
pip install ghostbit
```

## Basic Usage

### Encoding Files

```python
from ghostbit.audiostego.core.audio_multiformat_coder import AudioMultiFormatCoder, EncodeMode

# Create coder instance
coder = AudioMultiFormatCoder()

# Encode files
coder.encode_files_multi_format(
    carrier_file="music.wav",
    secret_files=["document.pdf", "photo.jpg"],
    output_file="encoded.wav",
    password="<STRONG_PASSWORD>",
    quality_mode=EncodeMode.NORMAL_QUALITY
)
```

### Decoding Files

```python
from ghostbit.audiostego import AudioMultiFormatCoder

# Create coder instance
coder = AudioMultiFormatCoder()

# Decode files
coder.decode_files_multi_format(
    encoded_file="encoded.wav",
    output_dir="extracted_files/",
    password="<STRONG_PASSWORD>"
)
```

### Analyzing Files

```python
from ghostbit.audiostego import AudioMultiFormatCoder

# Create coder instance
coder = AudioMultiFormatCoder()

# Check if file contains hidden data
coder.analyze_multi_format(
    audio_file="encoded.wav",
    password="<STRONG_PASSWORD>"
)
```

## Quality Modes

GH0STB1T: AUD10STEG0 supports three quality modes that balance capacity vs. audio quality:

| Mode | Ratio | Use Case |
|------|-------|----------|
| `LOW_QUALITY` | 2:1 | Maximum capacity, noticeable quality loss |
| `NORMAL_QUALITY` | 4:1 | Balanced - recommended for most cases |
| `HIGH_QUALITY` | 8:1 | Minimal capacity, imperceptible quality loss |

```python
from ghostbit.audiostego import AudioMultiFormatCoder, EncodeMode

# Create coder instance
coder = AudioMultiFormatCoder()

# Use high quality for music
coder.encode_files_multi_format(
    carrier_file="music.wav",
    secret_files=["secret.txt"],
    output_file="output.wav",
    quality_mode=EncodeMode.HIGH_QUALITY
)
```

## Supported Formats

**Input (Carrier):**
- WAV, FLAC, MP3, M4A, AIFF, AIF

**Output:**
- WAV, FLAC, M4A, AIFF, AIF

**Secret Files:**
- ANY file type (e.g., documents, images, videos, zip)


## Password Requirements

Generate a password with 12+ characters including mixed case, numbers, and symbols.

```python
import uuid

def generate_uuid_password() -> str:
    """Generate a password from UUID (128-bit random)"""
    return str(uuid.uuid4())
# Example
generate_uuid_password().replace('-', '')
```

**Why This Matters:**
- Password protects hidden data
- No password recovery; save password in a secure location for decode
- Weak passwords can be brute-forced using dictionary attacks


## Encryption

Always use encryption for sensitive data:

```python

# With password
coder.encode_files_multi_format(
    carrier_file="carrier.wav",
    secret_files=["confidential.pdf"],
    output_file="output.wav",
    password="<STRONG_PASSWORD>"  # AES-256 encryption
)

# Without encryption (not recommended)
coder.encode_files_multi_format(
    carrier_file="carrier.wav",
    secret_files=["public_data.txt"],
    output_file="output.wav"
    # No password = unencrypted
)
```

## Best Practices

1. **Check Capacity First**: Ensure carrier can hold your secret files
2. **Use Strong Passwords**: 12+ characters with mixed case, numbers, symbols
3. **Choose Right Quality**: NORMAL_QUALITY works for most cases
4. **Lossless Formats**: Use WAV or FLAC for output to preserve data
5. **Unique Passwords**: Don't reuse passwords across files
6. **Test Recovery**: Always test decoding before deleting originals

## Common Patterns

### Multiple Files

```python
# Hide multiple files at once
coder.encode_files_multi_format(
    carrier_file="long_audio.wav",
    secret_files=[
        "document1.pdf",
        "document2.docx",
        "photo.jpg",
        "video.mp4"
    ],
    output_file="output.wav",
    password="<STRONG_PASSWORD>"
)
```

### Format Conversion

```python
# Input MP3, output FLAC
coder.encode_files_multi_format(
    carrier_file="music.mp3",
    secret_files=["secret.zip"],
    output_file="encoded.flac",
    password="password"
)
```

### With Progress Callbacks

```python
def on_progress():
    print("Processing block...")

coder = MultiFormatCoder()
coder.on_encoded_element = on_progress

coder.encode_files_multi_format(
    carrier_file="large_file.wav",
    secret_files=["big_secret.zip"],
    output_file="output.wav"
)
```

## Error Handling

```python
from ghostbit.audiostego import (
    AudioMultiFormatCoder,
    AudioSteganographyException,
    KeyEnterCanceledException
)

try:
    coder = AudioMultiFormatCoder()
    coder.encode_files_multi_format(
        carrier_file="carrier.wav",
        secret_files=["secret.txt"],
        output_file="output.wav",
        password="password"
    )
except AudioSteganographyException as e:
    print(f"Encoding failed: {e}")
except KeyEnterCanceledException:
    print("Password entry cancelled")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Security Considerations

1. **Password Strength**: Use cryptographically strong passwords
2. **No Password Recovery**: Lost passwords cannot be recovered
3. **File Deletion**: Securely delete original files after encoding
4. **Transmission**: Encoded files appear as normal audio
5. **Deniability**: No obvious signs of hidden data

## Performance Tips

1. Use larger carrier files for better capacity
2. Compress secret files before encoding
3. Use NORMAL_QUALITY for balance of speed/capacity
4. Process multiple small files together rather than separately