# Capacity Planning

Guide for calculating and managing carrier capacity in GH0STB1T: 1MAGESTEG0.

## Overview

Understanding carrier capacity is crucial for successful encoding. This guide helps you calculate available space and plan your encoding strategy.

## Capacity Formula
```
Available Capacity = (Carrier Size - Header - Overhead) / Quality Mode Ratio
```

Where:
- **Carrier Size**: Size of the image file in bytes

## Checking Capacity

### Using Python API
```python
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

# Check if your files fit
secret_files = ["doc1.pdf", "doc2.txt"]
total_secret_size = sum(os.path.getsize(f) for f in secret_files)

if total_secret_size <= base.capacity_bytes:
    print("✓ Files will fit!")
else:
    print("✗ Files too large for carrier")
    print(f"Need: {total_secret_size:,} bytes")
    print(f"Have: {base.capacity_bytes:,} bytes")
```

## Optimization Strategies

### 1. Compress Before Encoding
```python
import zipfile

# Compress files first
with zipfile.ZipFile('secrets.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('large_file1.pdf')
    zf.write('large_file2.docx')

# Encode compressed file
coder.encode(
    cover_path="image.png",
    secret_files=["secrets.zip"],
)
```

### 2. Use Lossless Images as Carrier for Large Files
```python
# For large archives, use BMP or PNG as Carrier
coder.encode(
    cover_path="big_image.bmp",
    secret_files=["backup.tar.gz"],
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
            coder.encode(
                cover_path=carrier,
                secret_files=[chunk_file],
                password=<STRONG_PASSWORD>,
            )
```

## Common Issues

### "Not Enough Capacity" Error
```python
# Check capacity before encoding
def check_before_encode(carrier, secrets, quality):
    coder = ImageMultiFormatCoder()
    base = coder.calculate_capacity(
        image_path=carrier
    )
    
    total_size = sum(os.path.getsize(f) for f in secrets)
    
    if total_size > base.capacity_bytes:
        print(f"ERROR: Insufficient capacity")
        print(f"Required: {total_size:,} bytes")
        print(f"Available: {base.capacity_bytes:,} bytes")
        print(f"Shortfall: {total_size - base.capacity_bytes:,} bytes")
        
        # Suggest solutions
        print("\nSolutions:")
        print("1. Use larger carrier file")
        print("2. Compress secret files")
        print("3. Use lossless image file")
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
