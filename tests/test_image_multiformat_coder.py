#!/usr/bin/env python3
import os
import pytest
import struct
from PIL import Image
from typing import List
import tempfile

from ghostbit.imagestego.core.image_multiformat_coder import (
    ImageMultiFormatCoder,
    ImageMultiFormatCoderException,
    CapacityResult,
    AnalysisResult
)
from ghostbit.imagestego.core.image_steganography import (
    Algorithm,
    SecretFileInfoItem,
    ImageSteganographyException
)


"""
Tests for imagestego.core.image_multiformat_coder module
"""


class TestImageMultiFormatCoderInit:
    """Test ImageMultiFormatCoder initialization"""

    def test_initialization(self):
        """Test successful initialization"""
        coder = ImageMultiFormatCoder()
        
        assert hasattr(coder, 'algorithms')
        assert hasattr(coder, 'stats')
        assert Algorithm.LSB in coder.algorithms
        assert Algorithm.PALETTE in coder.algorithms
        assert Algorithm.SVG_XML in coder.algorithms

    def test_format_algorithms_mapping(self):
        """Test FORMAT_ALGORITHMS mapping"""
        assert ImageMultiFormatCoder.FORMAT_ALGORITHMS["PNG"] == Algorithm.LSB
        assert ImageMultiFormatCoder.FORMAT_ALGORITHMS["GIF"] == Algorithm.PALETTE
        assert ImageMultiFormatCoder.FORMAT_ALGORITHMS["SVG"] == Algorithm.SVG_XML
        assert ImageMultiFormatCoder.FORMAT_ALGORITHMS["JPEG"] == Algorithm.LSB
        assert ImageMultiFormatCoder.FORMAT_ALGORITHMS["WEBP"] == Algorithm.LSB


class TestFormatDetection:
    """Test format detection functionality"""

    @pytest.fixture
    def coder(self):
        """Create ImageMultiFormatCoder instance"""
        return ImageMultiFormatCoder()

    def test_detect_png_format(self, coder, tmp_path):
        """Test PNG format detection"""
        img = Image.new("RGB", (100, 100))
        path = tmp_path / "test.png"
        img.save(path)
        
        format = coder.detect_format(str(path))
        assert format == "PNG"

    def test_detect_jpeg_format(self, coder, tmp_path):
        """Test JPEG format detection"""
        img = Image.new("RGB", (100, 100))
        path = tmp_path / "test.jpg"
        img.save(path)
        
        format = coder.detect_format(str(path))
        assert format in ["JPEG", "JPG"]

    def test_detect_gif_format(self, coder, tmp_path):
        """Test GIF format detection"""
        img = Image.new("P", (100, 100))
        palette = list(range(256)) * 3
        img.putpalette(palette)
        path = tmp_path / "test.gif"
        img.save(path, format="GIF")
        
        format = coder.detect_format(str(path))
        assert format == "GIF"

    def test_detect_svg_format(self, coder, tmp_path):
        """Test SVG format detection"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="0" y="0" width="100" height="100" fill="blue"/>
</svg>"""
        path = tmp_path / "test.svg"
        path.write_text(svg_content)
        
        format = coder.detect_format(str(path))
        assert format == "SVG"

    def test_detect_webp_format(self, coder, tmp_path):
        """Test WEBP format detection"""
        img = Image.new("RGB", (100, 100))
        path = tmp_path / "test.webp"
        img.save(path, format="WEBP")
        
        format = coder.detect_format(str(path))
        assert format == "WEBP"

    def test_detect_bmp_format(self, coder, tmp_path):
        """Test BMP format detection"""
        img = Image.new("RGB", (100, 100))
        path = tmp_path / "test.bmp"
        img.save(path, format="BMP")
        
        format = coder.detect_format(str(path))
        assert format == "BMP"

    def test_detect_format_by_extension(self, coder, tmp_path):
        """Test format detection falls back to extension"""
        # Create a file that might not be recognized by PIL
        path = tmp_path / "test.unknown"
        path.write_bytes(b"fake image data")
        
        format = coder.detect_format(str(path))
        assert format == "UNKNOWN"


class TestAlgorithmSelection:
    """Test algorithm selection based on format"""

    @pytest.fixture
    def coder(self):
        """Create ImageMultiFormatCoder instance"""
        return ImageMultiFormatCoder()

    def test_select_lsb_for_png(self, coder):
        """Test LSB selection for PNG"""
        algorithm = coder.select_algorithm("PNG")
        assert algorithm == Algorithm.LSB

    def test_select_lsb_for_jpeg(self, coder):
        """Test LSB selection for JPEG"""
        algorithm = coder.select_algorithm("JPEG")
        assert algorithm == Algorithm.LSB

    def test_select_palette_for_gif(self, coder):
        """Test PALETTE selection for GIF"""
        algorithm = coder.select_algorithm("GIF")
        assert algorithm == Algorithm.PALETTE

    def test_select_svg_for_svg(self, coder):
        """Test SVG_XML selection for SVG"""
        algorithm = coder.select_algorithm("SVG")
        assert algorithm == Algorithm.SVG_XML

    def test_select_default_for_unknown(self, coder):
        """Test default LSB for unknown format"""
        algorithm = coder.select_algorithm("UNKNOWN_FORMAT")
        assert algorithm == Algorithm.LSB


class TestCapacityCalculation:
    """Test capacity calculation for various formats"""

    @pytest.fixture
    def coder(self):
        """Create ImageMultiFormatCoder instance"""
        return ImageMultiFormatCoder()

    def test_calculate_capacity_png(self, coder, tmp_path):
        """Test capacity calculation for PNG"""
        img = Image.new("RGB", (100, 100))
        path = tmp_path / "test.png"
        img.save(path)
        
        result = coder.calculate_capacity(str(path))
        
        assert isinstance(result, dict)
        assert result["format"] == "PNG"
        assert result["algorithm"] == "LSB"
        assert result["capacity_bytes"] == 3750
        assert result["capacity_kb"] == pytest.approx(3.662, rel=0.01)
        assert result["capacity_mb"] == pytest.approx(0.00357, rel=0.01)

    def test_calculate_capacity_gif(self, coder, tmp_path):
        """Test capacity calculation for GIF"""
        img = Image.new("P", (100, 100))
        palette = list(range(256)) * 3
        img.putpalette(palette)
        path = tmp_path / "test.gif"
        img.save(path, format="GIF")
        
        result = coder.calculate_capacity(str(path))
        
        assert result["format"] == "GIF"
        assert result["algorithm"] == "PALETTE"
        assert result["capacity_bytes"] > 0

    def test_calculate_capacity_svg(self, coder, tmp_path):
        """Test capacity calculation for SVG"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="0" y="0" width="100" height="100"/>
</svg>"""
        path = tmp_path / "test.svg"
        path.write_text(svg_content)
        
        result = coder.calculate_capacity(str(path))
        
        assert result["format"] == "SVG"
        assert result["algorithm"] == "SVG_XML"
        assert result["capacity_bytes"] > 1000000

    def test_calculate_capacity_large_image(self, coder, tmp_path):
        """Test capacity with large image"""
        img = Image.new("RGB", (1000, 1000))
        path = tmp_path / "large.png"
        img.save(path)
        
        result = coder.calculate_capacity(str(path))
        
        assert result["capacity_bytes"] == 375000

    def test_calculate_capacity_nonexistent_file(self, coder):
        """Test capacity calculation with nonexistent file"""
        with pytest.raises(ImageSteganographyException, match="not found"):
            coder.calculate_capacity("nonexistent.png")

    def test_calculate_capacity_animated_gif(self, coder, tmp_path):
        """Test capacity calculation for animated GIF"""
        frames = []
        for i in range(3):
            frame = Image.new('P', (300, 300))
            palette = [i for i in range(256)] * 3
            frame.putpalette(palette)
            for x in range(300):
                for y in range(300):
                    frame.putpixel((x, y), (x * y + i) % 256)
            frames.append(frame)
        
        path = tmp_path / "animated.gif"
        frames[0].save(
            path,
            save_all=True,
            append_images=frames[1:],
            duration=100,
            format="GIF"
        )
        
        result = coder.calculate_capacity(str(path))
        
        assert result["capacity_bytes"] > 95


class TestAnalyze:
    """Test image analysis functionality"""

    @pytest.fixture
    def coder(self):
        """Create ImageMultiFormatCoder instance"""
        return ImageMultiFormatCoder()

    def test_analyze_clean_png(self, coder, tmp_path):
        """Test analyzing PNG without hidden data"""
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        path = tmp_path / "clean.png"
        img.save(path)
        
        result = coder.analyze(str(path))
        
        assert isinstance(result, dict)
        assert result["has_hidden_data"] is False
        assert result["format"] == "PNG"
        assert result["algorithm"] is None
        assert result["encrypted"] is None

    def test_analyze_png_with_hidden_data(self, coder, tmp_path):
        """Test analyzing PNG with hidden data"""

        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret content")
        
        cover = Image.new("RGBA", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        item = SecretFileInfoItem(str(secret_file), is_in_add_list=True)
        output_dir = tmp_path / "encoded"
        output_dir.mkdir()
        
        coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password='test',
            show_stats=False
        )
        
        stego_path = output_dir / "cover_encoded.png"
        result = coder.analyze(str(stego_path))
        
        assert result["has_hidden_data"] is True
        assert result["algorithm"] == Algorithm.LSB
        assert result["encrypted"] is True

    def test_analyze_encrypted_image(self, coder, tmp_path):
        """Test analyzing image with encrypted hidden data"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret")
        
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        output_dir = tmp_path / "encoded"
        output_dir.mkdir()
        
        coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password="test123",
            show_stats=False
        )
        
        stego_path = output_dir / "cover_encoded.png"
        result = coder.analyze(str(stego_path))
        
        assert result["has_hidden_data"] is True
        assert result["encrypted"] is True

    def test_analyze_gif(self, coder, tmp_path):
        """Test analyzing GIF file"""
        static_gif = 'tests/testcases/test_static.gif'
        
        result = coder.analyze(str(static_gif))
        
        assert result["format"] == "GIF"
        assert result["has_hidden_data"] is False

    def test_analyze_svg(self, coder, tmp_path):
        """Test analyzing SVG file"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="0" y="0" width="100" height="100"/>
</svg>"""
        path = tmp_path / "test.svg"
        path.write_text(svg_content)
        
        result = coder.analyze(str(path))
        
        assert result["format"] == "SVG"
        assert result["has_hidden_data"] is False

    def test_analyze_nonexistent_file(self, coder):
        """Test analyzing nonexistent file"""
        with pytest.raises(ImageSteganographyException, match="not found"):
            coder.analyze("nonexistent.png")


class TestEncode:
    """Test encoding functionality"""

    @pytest.fixture
    def coder(self):
        """Create ImageMultiFormatCoder instance"""
        return ImageMultiFormatCoder()

    def test_encode_single_file_png(self, coder, tmp_path):
        """Test encoding single file into PNG"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret message")
        
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password='test',
            show_stats=False
        )
        
        assert os.path.exists(result_path)
        assert result_path.endswith("_encoded.png")

    def test_encode_multiple_files(self, coder, tmp_path):
        """Test encoding multiple files"""
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            f.write_text(f"Content {i}")
            files.append(str(f))
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            files,
            str(output_dir),
            password='test',
            show_stats=False
        )
        
        assert os.path.exists(result_path)

    def test_encode_with_password(self, coder, tmp_path):
        """Test encoding with password"""
        secret_file = tmp_path / "secret.bin"
        secret_file.write_bytes(b"Binary data")
        
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password="secure_password",
            show_stats=False
        )
        
        assert os.path.exists(result_path)

    def test_encode_gif(self, coder, tmp_path):
        """Test encoding into GIF"""
        secret_file = tmp_path / "data.txt"
        secret_file.write_text("Data")
        
        img = Image.new('P', (300, 300))
        img.putpalette([i for i in range(256)] * 3)
        for x in range(300):
            for y in range(300):
                img.putpixel((x, y), (x + y) % 256)
        cover_path = tmp_path / "cover.gif"
        img.save(cover_path, format="GIF")
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password='test',
            show_stats=False
        )
        
        assert os.path.exists(result_path)
        assert result_path.endswith(".gif")

    def test_encode_animated_gif(self, coder, tmp_path):
        """Test encoding into animated GIF"""
        secret_file = tmp_path / "data.txt"
        secret_file.write_text("data")
        
        frames = []
        for i in range(3):
            frame = Image.new('P', (300, 300))
            palette = [i for i in range(256)] * 3
            frame.putpalette(palette)
            for x in range(300):
                for y in range(300):
                    frame.putpixel((x, y), (x * y + i) % 256)

            frames.append(frame)
        
        cover_path = tmp_path / "animated.gif"
        frames[0].save(
            cover_path,
            save_all=True,
            append_images=frames[1:],
            duration=100,
            format="GIF"
        )
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password='test',
            show_stats=False
        )
        
        assert os.path.exists(result_path)
        
        with Image.open(result_path) as img:
            assert getattr(img, 'n_frames', 1) == 3

    def test_encode_svg(self, coder, tmp_path):
        """Test encoding into SVG"""
        secret_file = tmp_path / "secret.xml"
        secret_file.write_text("<data>content</data>")
        
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
    <circle cx="100" cy="100" r="50" fill="red"/>
</svg>"""
        cover_path = tmp_path / "cover.svg"
        cover_path.write_text(svg_content)
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password='test',
            show_stats=False
        )
        
        assert os.path.exists(result_path)
        assert result_path.endswith(".svg")

    def test_encode_jpeg_converts_to_png(self, coder, tmp_path):
        """Test that JPEG is converted to PNG for encoding"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret")
        
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.jpg"
        cover.save(cover_path, format="JPEG")
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password='test',
            show_stats=False
        )
        
        assert result_path.endswith(".png")

    def test_encode_file_too_large(self, coder, tmp_path):
        """Test encoding file that exceeds capacity"""

        secret_file = tmp_path / "large.bin"
        secret_file.write_bytes(b"X" * 100000)
        
        cover = Image.new("RGB", (5, 5))
        cover_path = tmp_path / "small_cover.png"
        cover.save(cover_path)
        
        output_dir = tmp_path / "output"
        
        with pytest.raises(ImageSteganographyException, match="too large"):
            coder.encode(
                str(cover_path),
                [str(secret_file)],
                str(output_dir),
                password='test',
                show_stats=False
            )

    def test_encode_nonexistent_cover(self, coder, tmp_path):
        """Test encoding with nonexistent cover image"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret")
        
        with pytest.raises(ImageSteganographyException, match="not found"):
            coder.encode(
                "nonexistent.png",
                [str(secret_file)],
                str(tmp_path / "output"),
                password='test',
                show_stats=False
            )

    def test_encode_nonexistent_secret(self, coder, tmp_path):
        """Test encoding with nonexistent secret file"""
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            ["nonexistent.txt"],
            str(output_dir),
            password='test',
            show_stats=False
        )
        
        assert os.path.exists(result_path)

    def test_encode_with_statistics(self, coder, tmp_path):
        """Test encoding with statistics generation"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret data")
        
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password='test',
            show_stats=True
        )
        
        assert os.path.exists(result_path)

    def test_encode_webp(self, coder, tmp_path):
        """Test encoding into WEBP"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("WebP secret")
        
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.webp"
        cover.save(cover_path, format="WEBP")
        
        output_dir = tmp_path / "output"
        
        result_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(output_dir),
            password='test',
            show_stats=False
        )
        
        assert os.path.exists(result_path)
        assert result_path.endswith(".webp")


class TestDecode:
    """Test decoding functionality"""

    @pytest.fixture
    def coder(self):
        """Create ImageMultiFormatCoder instance"""
        return ImageMultiFormatCoder()

    def test_decode_png_roundtrip(self, coder, tmp_path):
        """Test encode-decode roundtrip with PNG"""
        secret_file = tmp_path / "secret.txt"
        secret_content = "Secret message for testing"
        secret_file.write_text(secret_content)
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        encode_dir = tmp_path / "encoded"
        
        stego_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(encode_dir),
            password='test',
            show_stats=False
        )
        
        decode_dir = tmp_path / "decoded"
        
        result = coder.decode(stego_path, str(decode_dir), password='test')
        
        assert result == 0
        
        extracted_path = decode_dir / "secret.txt"
        assert extracted_path.exists()
        assert extracted_path.read_text() == secret_content

    def test_decode_with_password(self, coder, tmp_path):
        """Test decode with password"""
        secret_file = tmp_path / "secret.bin"
        secret_content = b"Encrypted content"
        secret_file.write_bytes(secret_content)
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        password = "my_secure_password"
        encode_dir = tmp_path / "encoded"
        
        stego_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(encode_dir),
            password=password,
            show_stats=False
        )
        
        decode_dir = tmp_path / "decoded"
        
        result = coder.decode(stego_path, str(decode_dir), password=password)
        
        assert result == 0
        extracted = decode_dir / "secret.bin"
        assert extracted.read_bytes() == secret_content

    def test_decode_wrong_password(self, coder, tmp_path):
        """Test decode with wrong password"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Content")
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        encode_dir = tmp_path / "encoded"
        
        stego_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(encode_dir),
            password="correct",
            show_stats=False
        )
        
        decode_dir = tmp_path / "decoded"
        
        result = coder.decode(stego_path, str(decode_dir), password="wrong")
        
        assert result == 1

    def test_decode_multiple_files(self, coder, tmp_path):
        """Test decoding multiple files"""
        files = {}
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            content = f"Content of file {i}"
            f.write_text(content)
            files[f.name] = content
        
        cover = Image.new("RGB", (400, 400))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        encode_dir = tmp_path / "encoded"
        
        stego_path = coder.encode(
            str(cover_path),
            list(str(tmp_path / name) for name in files.keys()),
            str(encode_dir),
            password='test',
            show_stats=False
        )
        
        decode_dir = tmp_path / "decoded"
        
        result = coder.decode(stego_path, str(decode_dir), password='test')
        
        assert result == 0
        
        for name, content in files.items():
            extracted = decode_dir / name
            assert extracted.exists()
            assert extracted.read_text() == content

    def test_decode_gif(self, coder, tmp_path):
        """Test decoding from GIF"""
        secret_file = tmp_path / "data.txt"
        secret_content = "GIF data"
        secret_file.write_text(secret_content)
        
        img = Image.new('P', (300, 300))
        img.putpalette([i for i in range(256)] * 3)
        for x in range(300):
            for y in range(300):
                img.putpixel((x, y), (x + y) % 256)
        cover_path = tmp_path / "cover.gif"
        img.save(cover_path, format="GIF")
        
        
        encode_dir = tmp_path / "encoded"
        
        stego_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(encode_dir),
            password='test',
            show_stats=False
        )
        
        decode_dir = tmp_path / "decoded"
        
        result = coder.decode(stego_path, str(decode_dir), password='test')
        
        assert result == 0
        extracted = decode_dir / "data.txt"
        assert extracted.read_text() == secret_content

    def test_decode_svg(self, coder, tmp_path):
        """Test decoding from SVG"""
        secret_file = tmp_path / "secret.json"
        secret_content = '{"key": "value"}'
        secret_file.write_text(secret_content)
        
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300">
    <rect x="50" y="50" width="200" height="200" fill="blue"/>
</svg>"""
        cover_path = tmp_path / "cover.svg"
        cover_path.write_text(svg_content)
        
        encode_dir = tmp_path / "encoded"
        
        stego_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(encode_dir),
            password='test',
            show_stats=False
        )
        
        decode_dir = tmp_path / "decoded"
        
        result = coder.decode(stego_path, str(decode_dir), password='test')
        
        assert result == 0
        extracted = decode_dir / "secret.json"
        assert extracted.read_text() == secret_content

    def test_decode_no_hidden_data(self, coder, tmp_path):
        """Test decoding image without hidden data"""
        clean_img = Image.new("RGB", (200, 200))
        clean_path = tmp_path / "clean.png"
        clean_img.save(clean_path)
        
        decode_dir = tmp_path / "decoded"
        
        result = coder.decode(str(clean_path), str(decode_dir), password='test')
        
        assert result == 0

    def test_decode_nonexistent_file(self, coder, tmp_path):
        """Test decoding nonexistent file"""
        with pytest.raises(ImageSteganographyException, match="not found"):
            coder.decode("nonexistent.png", str(tmp_path / "output"), password='test')


class TestGenerateStatistics:
    """Test statistics generation"""

    @pytest.fixture
    def coder(self):
        """Create ImageMultiFormatCoder instance"""
        return ImageMultiFormatCoder()

    def test_generate_statistics_png(self, coder, tmp_path):
        """Test generating statistics for PNG"""
        original = Image.new("RGB", (100, 100), color=(128, 128, 128))
        stego = Image.new("RGB", (100, 100), color=(129, 129, 129))
        
        original_path = tmp_path / "original.png"
        stego_path = tmp_path / "stego.png"
        
        original.save(original_path)
        stego.save(stego_path)
        
        coder.generate_statistics(
            "PNG",
            str(original_path),
            str(stego_path),
            stego
        )

    def test_generate_statistics_gif(self, coder, tmp_path):
        """Test generating statistics for GIF"""
        frames = []
        for i in range(2):
            img = Image.new("P", (100, 100), color=i * 50)
            palette = list(range(256)) * 3
            img.putpalette(palette)
            frames.append(img)
        
        original_path = tmp_path / "original.gif"
        stego_path = tmp_path / "stego.gif"
        
        frames[0].save(
            original_path,
            save_all=True,
            append_images=frames[1:],
            format="GIF"
        )
        frames[0].save(
            stego_path,
            save_all=True,
            append_images=frames[1:],
            format="GIF"
        )
        
        coder.generate_statistics(
            "GIF",
            str(original_path),
            str(stego_path),
            frames
        )

    def test_generate_statistics_svg(self, coder, tmp_path):
        """Test generating statistics for SVG"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="0" y="0" width="100" height="100"/>
</svg>"""
        original_path = tmp_path / "original.svg"
        stego_path = tmp_path / "stego.svg"
        
        original_path.write_text(svg_content)
        stego_path.write_text(svg_content)
        
        coder.generate_statistics(
            "SVG",
            str(original_path),
            str(stego_path),
            svg_content
        )


class TestIntegrationScenarios:
    """Test complete integration scenarios"""

    @pytest.fixture
    def coder(self):
        """Create ImageMultiFormatCoder instance"""
        return ImageMultiFormatCoder()

    def test_complete_workflow_png(self, coder, tmp_path):
        """Test complete workflow: capacity -> encode -> analyze -> decode"""
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        capacity = coder.calculate_capacity(str(cover_path))
        assert capacity["capacity_bytes"] > 1000
        
        secret_file = tmp_path / "secret.pdf"
        secret_file.write_bytes(b"PDF" * 100)
        
        encode_dir = tmp_path / "encoded"
        stego_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(encode_dir),
            password="test",
            show_stats=False
        )
        
        analysis = coder.analyze(stego_path)
        assert analysis["has_hidden_data"] is True
        assert analysis["encrypted"] is True
        
        decode_dir = tmp_path / "decoded"
        result = coder.decode(stego_path, str(decode_dir), password="test")
        assert result == 0
        
        extracted = decode_dir / "secret.pdf"
        assert extracted.exists()

    def test_multi_format_workflow(self, coder, tmp_path):
        """Test workflow with different formats"""
        secret_file = tmp_path / "data.txt"
        secret_file.write_text("Data")
        
        formats = [
            ("png", Image.new("RGB", (200, 200)), "PNG"),
            ("webp", Image.new("RGB", (200, 200)), "WEBP"),
        ]
        
        for ext, img, format_name in formats:
            cover_path = tmp_path / f"cover.{ext}"
            img.save(cover_path, format=format_name)
            
            encode_dir = tmp_path / f"encoded_{ext}"
            stego_path = coder.encode(
                str(cover_path),
                [str(secret_file)],
                str(encode_dir),
                password='test',
                show_stats=False
            )
            
            decode_dir = tmp_path / f"decoded_{ext}"
            result = coder.decode(stego_path, str(decode_dir), password='test')
            
            assert result == 0
            assert (decode_dir / "data.txt").exists()


class TestErrorHandling:
    """Test error handling"""

    @pytest.fixture
    def coder(self):
        """Create ImageMultiFormatCoder instance"""
        return ImageMultiFormatCoder()

    def test_encode_corrupted_image(self, coder, tmp_path):
        """Test encoding with corrupted image"""
        corrupted_file = tmp_path / "corrupted.png"
        corrupted_file.write_bytes(b"Not a real PNG file")
        
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret")
        
        with pytest.raises(Exception):
            coder.encode(
                str(corrupted_file),
                [str(secret_file)],
                str(tmp_path / "output"),
                password='test',
                show_stats=False
            )

    def test_decode_corrupted_stego(self, coder, tmp_path):
        """Test decoding corrupted stego image"""

        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("Secret")
        
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        encode_dir = tmp_path / "encoded"
        stego_path = coder.encode(
            str(cover_path),
            [str(secret_file)],
            str(encode_dir),
            password='test',
            show_stats=False
        )
        
        with open(stego_path, "rb") as f:
            data = bytearray(f.read())
        data[100:200] = b"\x00" * 100
        
        corrupted_path = tmp_path / "corrupted.png"
        with open(corrupted_path, "wb") as f:
            f.write(data)
        
        decode_dir = tmp_path / "decoded"

        result = coder.decode(str(corrupted_path), str(decode_dir), password='test')

        # assert result == 0
