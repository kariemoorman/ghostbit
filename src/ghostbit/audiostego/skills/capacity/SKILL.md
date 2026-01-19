# Capacity Planning

Guide for calculating and managing carrier capacity in GH0STB1T: AUD10STEG0.

## Overview

Understanding carrier capacity is crucial for successful encoding. This guide helps you calculate available space and plan your encoding strategy.

## Capacity Formula
```
Available Capacity = (Carrier Size - Header - Overhead) / Quality Mode Ratio
```

Where:
- **Carrier Size**: Size of the audio file in bytes
- **Header**: WAV header (typically 44 bytes)
- **Overhead**: Internal overhead (~104 bytes + 51 bytes per file)
- **Quality Mode Ratio**: 2, 4, or 8 depending on quality setting

## Checking Capacity

### Using Python API
```python
from ghostbit.audiostego import BaseFileInfoItem, EncodeMode
import os

# Create base file info
carrier_file = "music.wav"
base = BaseFileInfoItem(
    full_path=carrier_file,
    encode_mode=EncodeMode.NORMAL_QUALITY,
    wav_head_length=44
)

# Check capacity
print(f"Carrier file: {base.file_name}")
print(f"Total size: {base.file_size:,} bytes")
print(f"Max capacity: {base.max_inner_files_size:,} bytes")
print(f"Available: {base.remains_inner_files_size_mb}")

# Check if your files fit
secret_files = ["doc1.pdf", "doc2.txt"]
total_secret_size = sum(os.path.getsize(f) for f in secret_files)

if total_secret_size <= base.max_inner_files_size:
    print("✓ Files will fit!")
else:
    print("✗ Files too large for carrier")
    print(f"Need: {total_secret_size:,} bytes")
    print(f"Have: {base.max_inner_files_size:,} bytes")
```

### Quick Estimation

**Rule of Thumb:**
```
NORMAL_QUALITY (4:1): Capacity ≈ Carrier Size / 4
HIGH_QUALITY (8:1):   Capacity ≈ Carrier Size / 8
LOW_QUALITY (2:1):    Capacity ≈ Carrier Size / 2
```

**Examples:**
- 10 MB carrier @ NORMAL = ~2.5 MB capacity
- 50 MB carrier @ HIGH = ~6.25 MB capacity
- 100 MB carrier @ LOW = ~50 MB capacity

## Capacity by Duration

For CD-quality WAV (44.1kHz, 16-bit, stereo):

| Duration | File Size | NORMAL Capacity | HIGH Capacity |
|----------|-----------|-----------------|---------------|
| 1 minute | ~10 MB | ~2.5 MB | ~1.25 MB |
| 5 minutes | ~50 MB | ~12.5 MB | ~6.25 MB |
| 10 minutes | ~100 MB | ~25 MB | ~12.5 MB |
| 30 minutes | ~300 MB | ~75 MB | ~37.5 MB |
| 1 hour | ~600 MB | ~150 MB | ~75 MB |

## Optimization Strategies

### 1. Compress Before Encoding
```python
import zipfile

# Compress files first
with zipfile.ZipFile('secrets.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('large_file1.pdf')
    zf.write('large_file2.docx')

# Encode compressed file
coder.encode_files_multi_format(
    carrier_file="carrier.wav",
    secret_files=["secrets.zip"],  # Much smaller!
    output_file="output.wav"
)
```

### 2. Use Lower Quality for Large Files
```python
# For large archives, use LOW_QUALITY
coder.encode_files_multi_format(
    carrier_file="long_audio.wav",
    secret_files=["backup.tar.gz"],
    output_file="output.wav",
    quality_mode=EncodeMode.LOW_QUALITY  # Double capacity
)
```

### 3. Split Across Multiple Carriers
```python
# Split large file across multiple carriers
def split_and_encode(large_file, carriers, output_dir):
    file_size = os.path.getsize(large_file)
    chunk_size = file_size // len(carriers)
    
    # Split file
    with open(large_file, 'rb') as f:
        for i, carrier in enumerate(carriers):
            chunk = f.read(chunk_size)
            chunk_file = f"chunk_{i}.dat"
            
            with open(chunk_file, 'wb') as cf:
                cf.write(chunk)
            
            # Encode chunk
            coder.encode_files_multi_format(
                carrier_file=carrier,
                secret_files=[chunk_file],
                output_file=f"{output_dir}/encoded_{i}.wav"
            )
```

## Common Issues

### "Not Enough Capacity" Error
```python
# Check capacity before encoding
def check_before_encode(carrier, secrets, quality):
    base = BaseFileInfoItem(
        full_path=carrier,
        encode_mode=quality,
        wav_head_length=44
    )
    
    total_size = sum(os.path.getsize(f) for f in secrets)
    
    if total_size > base.max_inner_files_size:
        print(f"ERROR: Insufficient capacity")
        print(f"Required: {total_size:,} bytes")
        print(f"Available: {base.max_inner_files_size:,} bytes")
        print(f"Shortfall: {total_size - base.max_inner_files_size:,} bytes")
        
        # Suggest solutions
        print("\nSolutions:")
        print("1. Use larger carrier file")
        print("2. Compress secret files")
        print("3. Use lower quality mode")
        print("4. Split across multiple carriers")
        return False
    
    return True
```

## Best Practices

1. **Always check capacity first**
2. **Leave 10% buffer** for safety
3. **Compress large files** before encoding
4. **Use appropriate quality** for your use case
5. **Test with small files first**
