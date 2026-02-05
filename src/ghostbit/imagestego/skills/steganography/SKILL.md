# Image Steganography with GH0STB1T

Complete guide for hiding data in image files using the GH0STB1T: 1MAGESTEG0 Python package.

## Overview

GH0STB1T: 1MAGESTEG0 allows you to hide secret files inside image carriers using Palette, SVG XML, or LSB (Least Significant Bit) steganography. The data is embedded in the image samples in a way that's imperceptible to human perception.

## Installation

```bash
pip install git+https://github.com/kariemoorman/ghostbit.git@latest
```

## Basic Usage

### Encoding Files

```python
from ghostbit.imagestego import ImageMultiFormatCoder

# Create coder instance
coder = ImageMultiFormatCoder()

# Encode files
coder.encode(
    carrier_file="image.png",
    secret_files=["document.txt", "photo.jpg"],
    password="<STRONG_PASSWORD>",
)
```

### Decoding Files

```python
from ghostbit.imagestego import ImageMultiFormatCoder

# Create coder instance
coder = ImageMultiFormatCoder()

# Decode files
coder.decode(
    encoded_file="image_encoded.png",
    password="<STRONG_PASSWORD>",
)
```

### Analyzing Files

```python
from ghostbit.imagestego import ImageMultiFormatCoder

# Create coder instance
coder = ImageMultiFormatCoder()

# Check if file contains hidden data
coder.analyze(
    image_path="image.png"
)
```


## Supported Formats

**Input (Carrier):**
- PNG, JPEG, TIFF, SVG, GIF, BMP, WEBP

**Output:**
- PNG, TIFF, SVG, GIF, BMP, WEBP

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
coder.encode(
    cover_path="image.png",
    secret_files=["confidential.pdf"],
    password="<STRONG_PASSWORD>"  # AES-256 encryption
)

# Without encryption (not recommended)
coder.encode(
    cover_path="image.png",
    secret_files=["public_data.txt"],
    # No password = unencrypted
)
```

## Best Practices

1. **Check Capacity First**: Ensure carrier can hold your secret files
2. **Use Strong Passwords**: 12+ characters with mixed case, numbers, symbols
3. **Lossless Formats**: Use PNG or BMP for output to preserve data
4. **Unique Passwords**: Don't reuse passwords across files
5. **Test Recovery**: Always test decoding before deleting originals

## Security Considerations

1. **Password Strength**: Use cryptographically strong passwords
2. **No Password Recovery**: Lost passwords cannot be recovered
3. **File Deletion**: Securely delete original files after encoding
4. **Transmission**: Encoded files appear as normal images
5. **Deniability**: No obvious signs of hidden data

## Performance Tips

1. Use larger carrier files for better capacity
2. Compress secret files before encoding
3. Process multiple small files together rather than separately
