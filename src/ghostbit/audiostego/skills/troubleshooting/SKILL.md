# Troubleshooting Guide

Common issues and solutions when using AudioStego.

## Installation Issues

### pycryptodome Not Found

**Error:**
```
ModuleNotFoundError: No module named 'Crypto'
```

**Solution:**
```bash
pip install pycryptodome
```

### ffmpeg Not Available

**Error:**
```
Multi-format steganography support requires pydub or soundfile.
```

**Solution:**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Encoding Issues

### Insufficient Capacity

**Error:**
```
AudioSteganographyException: Secret file too large for carrier
```

**Solution:**
```python
# Check capacity first
from ghostbit.audiostego import BaseFileInfoItem, EncodeMode

base = BaseFileInfoItem(
    full_path="carrier.wav",
    encode_mode=EncodeMode.NORMAL_QUALITY,
    wav_head_length=44
)

print(f"Available capacity: {base.max_inner_files_size:,} bytes")

# Options:
# 1. Use larger carrier
# 2. Compress secret files
# 3. Use LOW_QUALITY mode
# 4. Split across multiple carriers
```

### Unsupported Format

**Error:**
```
AudioSteganographyException: Unsupported input format: .mp3
```

**Solution:**
```python
# Install audio libraries
pip install pydub soundfile

# Or convert to WAV first
ffmpeg -i input.mp3 output.wav
```

## Decoding Issues

### Wrong Password

**Error:**
```
AudioSteganographyException: Invalid password
```

**Solution:**
- Double-check password (case-sensitive)
- Ensure using same password as encoding
- No way to recover without correct password

### No Hidden Data Found

**Error:**
```
❌ No hidden data found in this file
```

**Possible Causes:**
1. File doesn't contain hidden data
2. File was compressed/re-encoded after embedding
3. Wrong file selected

**Solution:**
```python
# Verify file hasn't been modified
# - Check file size matches original
# - Ensure no lossy compression applied
# - Try analyzing with password
```

### Corrupted Output

**Issue:** Decoded files are corrupted or won't open

**Causes:**
- Carrier was modified after encoding
- Used lossy compression on output (MP3)
- Interrupted encoding/decoding

**Solution:**
```python
# Always use lossless formats for output
coder.encode_files_multi_format(
    carrier_file="input.wav",
    secret_files=["secret.pdf"],
    output_file="output.wav",
    password="password"
)
```

## Performance Issues

### Slow Encoding

**Solution:**
```python
# Increase buffer size
from ghostbit.audiostego import AudioMultiFormatCoder

coder = AudioMultiFormatCoder()
coder.set_buff_size(4 * 1024 * 1024)

# Or use lower quality for faster processing
coder.encode_files_multi_format(
    carrier_file="carrier.wav",
    secret_files=["secret.zip"],
    output_file="output.wav",
    quality_mode=EncodeMode.LOW_QUALITY
)
```

## Common Mistakes

### 1. Reusing Carrier Files

**Wrong:**
```python
# Encoding twice into same carrier
coder.encode_files_multi_format(
    carrier_file="carrier.wav",
    secret_files=["file1.txt"],
    output_file="output1.wav"
)
# ❌ Don't reuse output
coder.encode_files_multi_format(
    carrier_file="output1.wav",
    secret_files=["file2.txt"],
    output_file="output2.wav"
)
```

**Right:**
```python
# Use fresh carrier each time
coder.encode_files_multi_format(
    carrier_file="carrier1.wav",
    secret_files=["file1.txt", "file2.txt"],
    output_file="output.wav"
)
```

### 2. Not Checking Capacity

**Wrong:**
```python
# Encoding without checking
coder.encode_files_multi_format(
    carrier_file="small.wav",
    secret_files=["huge_file.zip"],
    output_file="output.wav"
)
```

**Right:**
```python
# Check capacity first
base = BaseFileInfoItem(
    full_path="small.wav",
    encode_mode=EncodeMode.NORMAL_QUALITY,
    wav_head_length=44
)

file_size = os.path.getsize("huge_file.zip")
if file_size <= base.max_inner_files_size:
    coder.encode_files_multi_format(...)
else:
    print("File too large!")
```

### 3. Using Lossy Output

**Wrong:**
```python
coder.encode_files_multi_format(
    carrier_file="carrier.wav",
    secret_files=["secret.pdf"],
    output_file="output.mp3"
)
```

**Right:**
```python
coder.encode_files_multi_format(
    carrier_file="carrier.wav",
    secret_files=["secret.pdf"],
    output_file="output.wav"
)
```

## Getting Help

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/kariemoorman/ghostbit/issues)
2. Enable verbose logging:
```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
```
3. Review error messages carefully
4. Test with simpler cases first
