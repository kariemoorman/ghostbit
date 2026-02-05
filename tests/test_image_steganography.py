#!/usr/bin/env python3
import os
import pytest
import secrets
import struct
from PIL import Image
from typing import List
import tempfile

from ghostbit.imagestego.core.image_steganograpy import (
    Algorithm,
    ImageSteganographyException,
    SecretFileInfoItem,
    BaseStego,
    LSBStego,
    PaletteStego,
    SVGStego,
)


"""
Tests for imagestego.core.image_steganography module
"""


class TestAlgorithmEnum:
    """Test Algorithm enum"""

    def test_algorithm_values(self):
        """Test algorithm enum values"""
        assert Algorithm.NONE == 0x00
        assert Algorithm.LSB == 0x01
        assert Algorithm.DCT == 0x02
        assert Algorithm.DWT == 0x03
        assert Algorithm.PALETTE == 0x04
        assert Algorithm.SVG_XML == 0x05

    def test_algorithm_int_enum(self):
        """Test that Algorithm is IntEnum"""
        assert Algorithm.LSB == 1
        assert int(Algorithm.LSB) == 1
        assert Algorithm(1) == Algorithm.LSB


class TestSecretFileInfoItem:
    """Test SecretFileInfoItem dataclass"""

    def test_creation_with_existing_file(self, tmp_path):
        """Test creating SecretFileInfoItem with existing file"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Hello, World!" * 100)
        
        item = SecretFileInfoItem(str(test_file), is_in_add_list=True)
        
        assert item.file_name == "test.txt"
        assert item.full_path == str(test_file)
        assert item.file_size > 0
        assert item.is_in_add_list is True

    def test_creation_with_nonexistent_file(self):
        """Test creating SecretFileInfoItem with nonexistent file"""
        item = SecretFileInfoItem("/nonexistent/file.txt", is_in_add_list=True)
        
        assert item.file_name == "file.txt"
        assert item.file_size == 0

    def test_creation_for_extraction(self):
        """Test creating SecretFileInfoItem for extraction"""
        item = SecretFileInfoItem(
            "extracted_file.pdf",
            is_in_add_list=False,
            file_size=1024,
            file_data=b"PDF content"
        )
        
        assert item.file_name == "extracted_file.pdf"
        assert item.file_size == 1024
        assert item.file_data == b"PDF content"

    def test_file_size_mb_property(self, tmp_path):
        """Test file_size_mb property"""
        test_file = tmp_path / "large.bin"
        test_file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2 MB
        
        item = SecretFileInfoItem(str(test_file), is_in_add_list=True)
        size_mb = item.file_size_mb
        
        assert "2.0 MB" in size_mb

    def test_file_size_mb_small_file(self, tmp_path):
        """Test file_size_mb with very small file"""
        test_file = tmp_path / "small.txt"
        test_file.write_bytes(b"tiny")
        
        item = SecretFileInfoItem(str(test_file), is_in_add_list=True)
        size_mb = item.file_size_mb
        
        assert "< 0.1 MB" in size_mb


class TestBaseStego:
    """Test BaseStego base class functionality"""

    @pytest.fixture
    def base_stego(self):
        """Create BaseStego instance"""
        return BaseStego()

    def test_magic_constant(self, base_stego):
        """Test MAGIC constant"""
        assert base_stego.MAGIC == b"STGX"

    def test_version_constant(self, base_stego):
        """Test VERSION constant"""
        assert base_stego.VERSION == 2

    def test_derive_key(self, base_stego):
        """Test key derivation"""
        password = "test_password"
        salt = secrets.token_bytes(16)
        
        key1 = base_stego._derive_key(password, salt)
        key2 = base_stego._derive_key(password, salt)
        
        assert len(key1) == 32
        assert key1 == key2
        
        different_salt = secrets.token_bytes(16)
        key3 = base_stego._derive_key(password, different_salt)
        assert key1 != key3

    def test_encrypt_decrypt_data(self, base_stego):
        """Test encryption and decryption"""
        password = "secure_password"
        data = b"Secret message that needs encryption"
        
        salt, nonce, ciphertext = base_stego._encrypt_data(data, password)
        
        assert len(salt) == 16
        assert len(nonce) == 12
        assert len(ciphertext) > len(data)
        
        decrypted = base_stego._decrypt_data(ciphertext, password, salt, nonce)
        assert decrypted == data

    def test_decrypt_wrong_password(self, base_stego):
        """Test decryption with wrong password"""
        password = "correct_password"
        data = b"Secret data"
        
        salt, nonce, ciphertext = base_stego._encrypt_data(data, password)
        
        with pytest.raises(ImageSteganographyException, match="Decryption failed"):
            base_stego._decrypt_data(ciphertext, "wrong_password", salt, nonce)

    def test_decrypt_corrupted_data(self, base_stego):
        """Test decryption with corrupted ciphertext"""
        password = "password"
        data = b"Data"
        
        salt, nonce, ciphertext = base_stego._encrypt_data(data, password)
        
        corrupted = bytearray(ciphertext)
        corrupted[0] ^= 0xFF
        
        with pytest.raises(ImageSteganographyException):
            base_stego._decrypt_data(bytes(corrupted), password, salt, nonce)

    def test_build_payload_single_file(self, base_stego, tmp_path):
        """Test building payload with single file"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret content")
        
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        payload = base_stego.build_payload([item], Algorithm.LSB, password=None)
        
        assert payload[:4] == b"STGX"
        assert payload[4] == 2
        assert payload[5] == Algorithm.LSB
        assert payload[6] == 0 

    def test_build_payload_with_encryption(self, base_stego, tmp_path):
        """Test building encrypted payload"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret content")
        
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        payload = base_stego.build_payload([item], Algorithm.LSB, password="password123")
        
        assert payload[:4] == b"STGX"
        assert payload[6] == 1

    def test_build_payload_multiple_files(self, base_stego, tmp_path):
        """Test building payload with multiple files"""
        files = []
        for i in range(3):
            secret_file = tmp_path / f"secret{i}.txt"
            secret_file.write_text(f"Content {i}")
            files.append(SecretFileInfoItem(str(secret_file), is_in_add_list=True))
        
        payload = base_stego.build_payload(files, Algorithm.LSB, password=None)
        
        assert len(payload) > 0
        assert payload[:4] == b"STGX"

    def test_build_payload_long_filename(self, base_stego, tmp_path):
        """Test payload with very long filename (should be truncated)"""
        long_name = "a" * 50 + ".txt"
        secret_file = tmp_path / long_name
        secret_file.write_text("Content")
        
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        payload = base_stego.build_payload([item], Algorithm.LSB, password=None)
        
        assert len(payload) > 0

    def test_parse_payload_unencrypted(self, base_stego, tmp_path):
        """Test parsing unencrypted payload"""
        secret_file = tmp_path / "test.txt"
        secret_content = b"Test content for parsing"
        secret_file.write_bytes(secret_content)
        
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        payload = base_stego.build_payload([item], Algorithm.LSB, password=None)
        
        extracted_files, algorithm = base_stego.parse_payload(payload, password=None)
        
        assert len(extracted_files) == 1
        assert extracted_files[0].file_name == "test.txt"
        assert extracted_files[0].file_data == secret_content
        assert algorithm == Algorithm.LSB

    def test_parse_payload_encrypted(self, base_stego, tmp_path):
        """Test parsing encrypted payload"""
        secret_file = tmp_path / "secret.bin"
        secret_content = b"Encrypted content"
        secret_file.write_bytes(secret_content)
        
        password = "my_password"
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        payload = base_stego.build_payload([item], Algorithm.LSB, password=password)
        
        extracted_files, algorithm = base_stego.parse_payload(payload, password=password)
        
        assert len(extracted_files) == 1
        assert extracted_files[0].file_data == secret_content

    def test_parse_payload_encrypted_no_password(self, base_stego, tmp_path):
        """Test parsing encrypted payload without password"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Content")
        
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        payload = base_stego.build_payload([item], Algorithm.LSB, password="password")
        
        with pytest.raises(ImageSteganographyException, match="Password required"):
            base_stego.parse_payload(payload, password=None)

    def test_parse_payload_wrong_password(self, base_stego, tmp_path):
        """Test parsing with wrong password"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Content")
        
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        payload = base_stego.build_payload([item], Algorithm.LSB, password="correct")
        
        with pytest.raises(ImageSteganographyException, match="Decryption failed"):
            base_stego.parse_payload(payload, password="wrong")

    def test_parse_payload_invalid_magic(self, base_stego):
        """Test parsing payload with invalid magic number"""
        invalid_payload = b"XXXX" + b"\x02\x01\x00" + b"\x00" * 20
        
        with pytest.raises(ImageSteganographyException, match="magic number mismatch"):
            base_stego.parse_payload(invalid_payload)

    def test_parse_payload_too_short(self, base_stego):
        """Test parsing payload that's too short"""
        short_payload = b"STGX"
        
        with pytest.raises(ImageSteganographyException, match="too short"):
            base_stego.parse_payload(short_payload)

    def test_parse_payload_unsupported_version(self, base_stego):
        """Test parsing payload with unsupported version"""
        payload = b"STGX" + b"\x99\x01\x00" + b"\x00" * 20
        
        with pytest.raises(ImageSteganographyException, match="Unsupported version"):
            base_stego.parse_payload(payload)

    def test_parse_payload_corrupted_compression(self, base_stego):
        """Test parsing payload with corrupted compressed data"""

        payload = b"STGX\x02\x01\x00" + struct.pack(">I", 10) + b"corrupted!"
        
        with pytest.raises(ImageSteganographyException, match="decompression failed"):
            base_stego.parse_payload(payload)


class TestLSBStego:
    """Test LSB steganography implementation"""

    @pytest.fixture
    def lsb_stego(self):
        """Create LSBStego instance"""
        return LSBStego()

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a test image"""
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        path = tmp_path / "test.png"
        img.save(path)
        return str(path)

    def test_get_capacity(self, lsb_stego, test_image):
        """Test capacity calculation"""
        capacity = lsb_stego.get_capacity(test_image)
        
        # 100x100 pixels * 3 channels / 8 bits = 3750 bytes
        assert capacity == 3750

    def test_get_capacity_large_image(self, lsb_stego, tmp_path):
        """Test capacity with larger image"""
        img = Image.new("RGB", (1000, 1000))
        path = tmp_path / "large.png"
        img.save(path)
        
        capacity = lsb_stego.get_capacity(str(path))
        assert capacity == 375000  # 1000*1000*3/8

    def test_encode_small_data(self, lsb_stego, test_image):
        """Test encoding small amount of data"""
        data = b"Hello, World!"
        
        stego_img = lsb_stego.encode(test_image, data)
        
        assert isinstance(stego_img, Image.Image)
        assert stego_img.size == (100, 100)
        assert stego_img.mode == "RGBA"

    def test_encode_decode_roundtrip(self, lsb_stego, test_image):
        """Test encode-decode roundtrip"""
        original_data = b"Secret message" * 10
        
        stego_img = lsb_stego.encode(test_image, original_data)
        
        # Save and reload to test persistence
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            stego_img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            decoded_data = lsb_stego.decode(tmp_path, len(original_data))
            assert decoded_data == original_data
        finally:
            os.unlink(tmp_path)

    def test_encode_maximum_capacity(self, lsb_stego, test_image):
        """Test encoding at maximum capacity"""
        capacity = lsb_stego.get_capacity(test_image)
        data = b"X" * capacity
        
        stego_img = lsb_stego.encode(test_image, data)
        assert isinstance(stego_img, Image.Image)

    def test_decode_correct_length(self, lsb_stego, test_image):
        """Test decoding with correct data length"""
        data = b"Test data for decoding"
        
        stego_img = lsb_stego.encode(test_image, data)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            stego_img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            decoded = lsb_stego.decode(tmp_path, len(data))
            assert decoded == data
        finally:
            os.unlink(tmp_path)

    def test_encode_seq(self, lsb_stego, test_image):
        """Test sequential encoding"""
        data = b"Sequential data"
        
        stego_img = lsb_stego.encode_seq(test_image, data)
        
        assert isinstance(stego_img, Image.Image)
        assert stego_img.mode == "RGBA"

    def test_decode_seq(self, lsb_stego, test_image):
        """Test sequential decoding"""
        data = b"Sequential test"
        
        stego_img = lsb_stego.encode_seq(test_image, data)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            stego_img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            decoded = lsb_stego.decode_seq(tmp_path, len(data))
            assert decoded == data
        finally:
            os.unlink(tmp_path)

    def test_encode_preserves_image_size(self, lsb_stego, test_image):
        """Test that encoding preserves image dimensions"""
        original = Image.open(test_image)
        original_size = original.size
        
        data = b"Some data"
        stego_img = lsb_stego.encode(test_image, data)
        
        assert stego_img.size == original_size

    def test_encode_invalid_image(self, lsb_stego, tmp_path):
        """Test encoding with invalid image file"""
        invalid_file = tmp_path / "not_an_image.txt"
        invalid_file.write_text("This is not an image")
        
        with pytest.raises(ImageSteganographyException):
            lsb_stego.encode(str(invalid_file), b"data")

    def test_decode_invalid_image(self, lsb_stego, tmp_path):
        """Test decoding from invalid image file"""
        invalid_file = tmp_path / "not_an_image.txt"
        invalid_file.write_text("This is not an image")
        
        with pytest.raises(ImageSteganographyException):
            lsb_stego.decode(str(invalid_file), 100)

    def test_key_consistency(self, lsb_stego):
        """Test that the key attribute is set correctly"""
        assert hasattr(lsb_stego, 'key')
        assert lsb_stego.key == 43


class TestPaletteStego:
    """Test Palette/GIF steganography implementation"""

    @pytest.fixture
    def palette_stego(self):
        """Create PaletteStego instance"""
        return PaletteStego()

    @pytest.fixture
    def static_gif(self, tmp_path):
        """Create a static GIF"""
        img = Image.new("P", (100, 100), color=0)
        palette = list(range(256)) * 3
        img.putpalette(palette)
        path = tmp_path / "static.gif"
        img.save(path, format="GIF")
        return str(path)

    @pytest.fixture
    def animated_gif(self, tmp_path):
        """Create an animated GIF"""
        frames = []
        for i in range(5):
            img = Image.new("P", (100, 100), color=i * 30)
            palette = list(range(256)) * 3
            img.putpalette(palette)
            frames.append(img)
        
        path = tmp_path / "animated.gif"
        frames[0].save(
            path,
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0,
            format="GIF"
        )
        return str(path)

    def test_get_capacity_static(self, palette_stego):
        """Test capacity calculation for static GIF"""
        static_gif = 'tests/testcases/test_static.gif'
        capacity = palette_stego.get_capacity(static_gif)
        
        assert capacity == 96

    def test_get_capacity_animated(self, palette_stego):
        """Test capacity calculation for animated GIF"""
        animated_gif = 'tests/testcases/test_animated.gif'
        capacity = palette_stego.get_capacity(animated_gif)
        
        assert capacity == 96

    def test_get_capacity_nonexistent(self, palette_stego):
        """Test capacity with nonexistent file"""
        with pytest.raises(ImageSteganographyException):
            palette_stego.get_capacity("nonexistent.gif")

    def test_get_capacity_non_gif(self, palette_stego, tmp_path):
        """Test capacity with non-GIF file"""
        img = Image.new("RGB", (100, 100))
        path = tmp_path / "not_gif.png"
        img.save(path)
        
        with pytest.raises(ImageSteganographyException, match="Not a GIF"):
            palette_stego.get_capacity(str(path))

    def test_encode_static_gif(self, palette_stego):
        """Test encoding into static GIF"""
        payload = b"Hello GIF"
        static_gif = 'tests/testcases/test_static.gif'
        result = palette_stego.encode(static_gif, payload)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Image.Image)

    def test_encode_animated_gif(self, palette_stego):
        """Test encoding into animated GIF"""
        payload = b"Animated secret"
        animated_gif = 'tests/testcases/test_animated.gif'
        result = palette_stego.encode(animated_gif, payload)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(frame, Image.Image) for frame in result)

    def test_encode_payload_too_large(self, palette_stego):
        """Test encoding payload larger than capacity"""
        static_gif = 'tests/testcases/test_static.gif'
        capacity = palette_stego.get_capacity(static_gif)
        payload = b"X" * (capacity + 100)
        
        with pytest.raises(ImageSteganographyException, match="too large"):
            palette_stego.encode(static_gif, payload)

    def test_encode_decode_roundtrip_static(self, palette_stego, tmp_path):
        """Test encode-decode roundtrip with static GIF"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret content")
        static_gif = 'tests/testcases/test_static.gif'
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        
        payload = palette_stego.build_payload([item], Algorithm.PALETTE, password=None)
        
        frames = palette_stego.encode(static_gif, payload)
        
        stego_path = tmp_path / "stego.gif"
        frames[0].save(stego_path, format="GIF")
        
        decoded_payload = palette_stego.decode(str(stego_path))
        
        extracted_files, algorithm = palette_stego.parse_payload(decoded_payload)
        
        assert len(extracted_files) == 1
        assert extracted_files[0].file_name == "secret.txt"

    def test_encode_decode_roundtrip_animated(self, palette_stego, tmp_path):
        """Test encode-decode roundtrip with animated GIF"""
        secret_file = tmp_path / "data.bin"
        secret_file.write_bytes(b"Binary data" * 10)
        animated_gif = 'tests/testcases/test_animated.gif'
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        
        payload = palette_stego.build_payload([item], Algorithm.PALETTE, password=None)
        
        frames = palette_stego.encode(animated_gif, payload)
        
        stego_path = tmp_path / "stego_animated.gif"
        frames[0].save(
            stego_path,
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0,
            format="GIF"
        )
        
        decoded_payload = palette_stego.decode(str(stego_path))
        extracted_files, _ = palette_stego.parse_payload(decoded_payload)
        
        assert len(extracted_files) == 1

    def test_decode_no_hidden_data(self, palette_stego):
        """Test decoding GIF without hidden data"""
        static_gif = 'tests/testcases/test_static.gif'
        result = palette_stego.decode(static_gif)
        assert result == None

    def test_decode_nonexistent_file(self, palette_stego):
        """Test decoding nonexistent file"""
        with pytest.raises(ImageSteganographyException):
            palette_stego.decode("nonexistent.gif")

    def test_bits_to_bytes(self, palette_stego):
        """Test _bits_to_bytes helper method"""
        bits = [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1]
        result = palette_stego._bits_to_bytes(bits)
        assert result == b"He"

    def test_bits_to_bytes_incomplete(self, palette_stego):
        """Test _bits_to_bytes with incomplete byte"""
        bits = [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1]
        result = palette_stego._bits_to_bytes(bits)
        assert len(result) == 1

    def test_extract_all_bits_from_gif(self, palette_stego):
        """Test extracting bits from GIF"""
        static_gif = 'tests/testcases/test_static.gif'
        bits = palette_stego._extract_all_bits(static_gif)
        
        assert isinstance(bits, list)
        assert len(bits) > 0
        assert all(bit in [0, 1] for bit in bits)

    def test_encode_static_helper(self, palette_stego):
        """Test _encode_static helper method"""
        img = Image.new("P", (50, 50), color=0)
        palette = list(range(256)) * 3
        img.putpalette(palette)
        
        bits = "01010101" * 10
        result = palette_stego._encode_static(img, bits)
        
        assert isinstance(result, Image.Image)
        assert result.mode == "P"

    def test_encode_animated_helper(self, palette_stego):
        """Test _encode_animated helper method"""
        frames_img = Image.new("P", (50, 50), color=0)
        palette = list(range(256)) * 3
        frames_img.putpalette(palette)
        
        bits = "01010101" * 10
        result = palette_stego._encode_animated(frames_img, bits, n_frames=1)
        
        assert isinstance(result, list)
        assert len(result) == 1


class TestSVGStego:
    """Test SVG steganography implementation"""

    @pytest.fixture
    def svg_stego(self):
        """Create SVGStego instance"""
        return SVGStego()

    @pytest.fixture
    def simple_svg(self, tmp_path):
        """Create a simple SVG file"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
    <circle cx="50" cy="50" r="30" fill="red"/>
</svg>"""
        path = tmp_path / "simple.svg"
        path.write_text(svg_content)
        return str(path)

    def test_get_capacity(self, svg_stego, simple_svg):
        """Test SVG capacity calculation"""
        capacity = svg_stego.get_capacity(simple_svg)
        
        assert capacity > 0
        assert capacity >= 1024 * 1024

    def test_encode_small_data(self, svg_stego, simple_svg):
        """Test encoding small data into SVG"""
        data = b"Hidden message"
        
        result = svg_stego.encode(simple_svg, data)
        
        assert isinstance(result, str)
        assert "STGX:" in result
        assert "</svg>" in result

    def test_encode_large_data(self, svg_stego, simple_svg):
        """Test encoding larger data"""
        data = b"X" * 10000
        
        result = svg_stego.encode(simple_svg, data)
        
        assert isinstance(result, str)
        assert "STGX:" in result

    def test_encode_decode_roundtrip(self, svg_stego, simple_svg, tmp_path):
        """Test SVG encode-decode roundtrip"""
        original_data = b"Secret SVG data with special chars: !@#$%"
        
        encoded_svg = svg_stego.encode(simple_svg, original_data)
        
        stego_path = tmp_path / "stego.svg"
        with open(stego_path, "w") as f:
            f.write(encoded_svg)
        
        decoded_data = svg_stego.decode(str(stego_path))
        
        assert decoded_data == original_data

    def test_encode_preserves_svg_structure(self, svg_stego, simple_svg):
        """Test that encoding preserves SVG structure"""
        original_content = open(simple_svg).read()
        data = b"Data"
        
        encoded = svg_stego.encode(simple_svg, data)
        
        assert "<rect" in encoded
        assert "<circle" in encoded
        assert "<!-- STGX:" in encoded

    def test_decode_no_hidden_data(self, svg_stego, simple_svg):
        """Test decoding SVG without hidden data"""
        result = svg_stego.decode(simple_svg)
        assert result == None

    def test_decode_invalid_base64(self, svg_stego, tmp_path):
        """Test decoding with invalid base64 data"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
    <!-- STGX:NotValidBase64!@# -->
</svg>"""
        path = tmp_path / "invalid.svg"
        path.write_text(svg_content)
        
        result = svg_stego.decode(str(path))
        assert result == None
        

    def test_encode_svg_without_closing_tag(self, svg_stego, tmp_path):
        """Test encoding SVG without </svg> tag"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="80"/>
"""  # Missing </svg>
        path = tmp_path / "no_close.svg"
        path.write_text(svg_content)
        
        data = b"Test"
        result = svg_stego.encode(str(path), data)
        
        # Should append comment even without </svg>
        assert "STGX:" in result

    def test_encode_with_complete_payload(self, svg_stego, simple_svg, tmp_path):
        """Test encoding with complete steganography payload"""
        secret_file = tmp_path / "secret.pdf"
        secret_file.write_bytes(b"PDF content here")
        
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        payload = svg_stego.build_payload([item], Algorithm.SVG_XML, password=None)
        
        encoded = svg_stego.encode(simple_svg, payload)
        
        # Save and decode
        stego_path = tmp_path / "stego.svg"
        with open(stego_path, "w") as f:
            f.write(encoded)
        
        decoded_payload = svg_stego.decode(str(stego_path))
        extracted_files, algorithm = svg_stego.parse_payload(decoded_payload)
        
        assert len(extracted_files) == 1
        assert extracted_files[0].file_name == "secret.pdf"
        assert algorithm == Algorithm.SVG_XML


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""

    def test_multiple_files_lsb(self, tmp_path):
        """Test hiding multiple files with LSB"""
        # Create secret files
        file1 = tmp_path / "doc1.txt"
        file1.write_text("Document 1 content")
        file2 = tmp_path / "doc2.txt"
        file2.write_text("Document 2 content")
        
        items = [
            SecretFileInfoItem(str(file1), is_in_add_list=True),
            SecretFileInfoItem(str(file2), is_in_add_list=True),
        ]
        
        # Create cover image
        cover = Image.new("RGB", (500, 500), color=(100, 100, 100))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        # Encode
        lsb = LSBStego()
        payload = lsb.build_payload(items, Algorithm.LSB, password="test123")
        stego_img = lsb.encode(str(cover_path), payload)
        
        # Save
        stego_path = tmp_path / "stego.png"
        stego_img.save(stego_path)
        
        # Decode
        decoded_payload = lsb.decode(str(stego_path), len(payload))
        extracted, _ = lsb.parse_payload(decoded_payload, password="test123")
        
        assert len(extracted) == 2
        assert {f.file_name for f in extracted} == {"doc1.txt", "doc2.txt"}

    def test_encrypted_gif_workflow(self, tmp_path):
        """Test complete encrypted GIF workflow"""
        # Create secret file
        secret = tmp_path / "confidential.bin"
        secret.write_bytes(b"Confidential" * 2)
        
        item = SecretFileInfoItem(str(secret), is_in_add_list=True)
        
        # Create GIF
        frames = []
        for i in range(3):
            frame = Image.new('P', (300, 300))
            palette = [i for i in range(256)] * 3
            frame.putpalette(palette)
            for x in range(300):
                for y in range(300):
                    frame.putpixel((x, y), (x * y + i) % 256)

            frames.append(frame)

        gif_path = f'{tmp_path}/carrier.gif'
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=100,
            format="GIF"
        )
        
        # Encode with encryption
        palette_stego = PaletteStego()
        password = "secure_password"
        payload = palette_stego.build_payload([item], Algorithm.PALETTE, password=password)
        
        encoded_frames = palette_stego.encode(gif_path, payload)
        
        # Save
        stego_path = tmp_path / "stego.gif"
        encoded_frames[0].save(
            stego_path,
            save_all=True,
            append_images=encoded_frames[1:],
            duration=100,
            format="GIF"
        )
        
        # Decode
        decoded_payload = palette_stego.decode(str(stego_path))
        extracted, _ = palette_stego.parse_payload(decoded_payload, password=password)
        
        assert len(extracted) == 1
        assert extracted[0].file_name == "confidential.bin"

    def test_svg_with_binary_data(self, tmp_path):
        """Test SVG steganography with binary data"""
        # Create SVG
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
    <rect x="0" y="0" width="200" height="200" fill="green"/>
</svg>"""
        svg_path = tmp_path / "image.svg"
        svg_path.write_text(svg_content)
        
        # Create binary secret
        binary_secret = tmp_path / "data.bin"
        binary_secret.write_bytes(bytes(range(256)) * 10)
        
        item = SecretFileInfoItem(str(binary_secret), is_in_add_list=True)
        
        # Encode
        svg_stego = SVGStego()
        payload = svg_stego.build_payload([item], Algorithm.SVG_XML, password=None)
        encoded = svg_stego.encode(str(svg_path), payload)
        
        # Save
        stego_path = tmp_path / "stego.svg"
        with open(stego_path, "w") as f:
            f.write(encoded)
        
        # Decode
        decoded_payload = svg_stego.decode(str(stego_path))
        extracted, _ = svg_stego.parse_payload(decoded_payload)
        
        assert len(extracted) == 1
        assert extracted[0].file_data == binary_secret.read_bytes()


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_encode_empty_data(self, tmp_path):
        """Test encoding empty data"""
        img = Image.new("RGB", (100, 100))
        path = tmp_path / "test.png"
        img.save(path)
        
        lsb = LSBStego()
        # Empty data should still work
        stego = lsb.encode(str(path), b"")
        assert isinstance(stego, Image.Image)

    def test_capacity_calculation_errors(self, tmp_path):
        """Test capacity calculation with problematic files"""
        # Non-image file
        txt_file = tmp_path / "text.txt"
        txt_file.write_text("Not an image")
        
        lsb = LSBStego()
        with pytest.raises(ImageSteganographyException):
            lsb.get_capacity(str(txt_file))

    def test_payload_with_unicode_filename(self, tmp_path):
        """Test payload with Unicode characters in filename"""
        secret = tmp_path / "файл.txt"  # Cyrillic characters
        secret.write_text("Content")
        
        item = SecretFileInfoItem(str(secret), is_in_add_list=True)
        base = BaseStego()
        payload = base.build_payload([item], Algorithm.LSB, password=None)
        
        # Should handle Unicode gracefully
        assert len(payload) > 0
