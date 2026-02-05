# Troubleshooting Guide

Common issues and solutions when using GH0STB1T: 1MAGESTEG0.

## Installation Issues

### Python Package Not Found

**Error:**
```
ModuleNotFoundError: No module named 'PyWavelets'
```

**Solution:**
```bash
pip install PyWavelets
```


## Encoding Issues

### Insufficient Capacity

**Error:**
```
ImageSteganographyException: Secret file too large for carrier
```

**Solution:**
```python
# Check capacity first
from ghostbit.imagestego import ImageMultiFormatCoder
import os

# Create base file info
carrier_file = "image.png"
coder = ImageMultiFormatCoder()
base = coder.calculate_capacity(
    image_path=carrier_file
)

# Check capacity
print(f"Carrier file format: {base.format}")
print(f"Max capacity: {base.capacity_bytes:,} bytes")

# Options:
# 1. Use larger carrier
# 2. Compress secret files
# 3. Use Lossless images (BMP, PNG)
# 4. Split across multiple carriers
```

### Unsupported Format

**Error:**
```
ImageMultiFormatCoderException: File format not supported
```

**Solution:**
```python
# Install PIL
pip install pillow

from PIL import Image

# Open an existing image
img = Image.open("image.heic")

# Save as BMP
img.save("image.bmp")
```

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


## Common Mistakes

### Reusing Carrier Files

**Wrong:**
```python
# Encoding twice into same carrier
coder.encode(
    carrier_file="image.png",
    secret_files=["file1.txt"],
)
# ❌ Don't reuse output
coder.encode(
    carrier_file="image_encoded.png",
    secret_files=["file2.txt"],
)
```

**Correct:**
```python
# Use fresh carrier each time
coder.encode(
    carrier_file="image.png",
    secret_files=["file1.txt", "file2.txt"],
)

coder.encode(
    carrier_file="different_image.png",
    secret_files=["file3.txt", "file4.txt"],
)
```


## Getting Help

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/kariemoorman/ghostbit/issues)
2. Review error messages carefully
3. Test with simpler cases first
