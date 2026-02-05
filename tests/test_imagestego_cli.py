#!/usr/bin/env python3
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call
from PIL import Image
import argparse

from ghostbit.imagestego.cli.imagestego_cli import (
    ImageStegoCLI,
    main,
)

from ghostbit.imagestego.core.image_multiformat_coder import ImageMultiFormatCoder, ImageMultiFormatCoderException


"""
Tests for imagestego.cli.imagestego_cli module
"""


class TestImageStegoCLIInit:
    """Test ImageStegoCLI initialization"""

    def test_initialization_default(self):
        """Test default initialization"""
        cli = ImageStegoCLI()
        assert cli.verbose is False

    def test_initialization_verbose(self):
        """Test initialization with verbose flag"""
        cli = ImageStegoCLI(verbose=True)
        assert cli.verbose is True


class TestEncodeCommand:
    """Test encode command functionality"""

    @pytest.fixture
    def cli(self):
        """Create CLI instance"""
        return ImageStegoCLI()

    @pytest.fixture
    def test_files(self, tmp_path):
        """Create test files"""
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "secret.txt"
        secret.write_text("Secret content")
        
        return str(cover_path), [str(secret)]

    def test_encode_without_password(self, cli, test_files, tmp_path, monkeypatch):
        """Test encoding without password (with confirmation)"""
        cover_path, secret_files = test_files
        
        # Mock user input to confirm
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        result = cli.encode_command(
            cover_path,
            secret_files,
            file_password=None,
            show_stats=False
        )
        
        assert result == 0

        output_path = os.path.join("output", "encoded", "cover_encoded.png")

        assert os.path.exists(output_path)

    def test_encode_abort_no_password(self, cli, test_files, monkeypatch):
        """Test encoding abort when declining to continue without password"""
        cover_path, secret_files = test_files
        
        monkeypatch.setattr('builtins.input', lambda _: 'n')
        
        with pytest.raises(SystemExit):
            cli.encode_command(
                cover_path,
                secret_files,
                file_password=None,
                show_stats=False
            )

    def test_encode_with_password_string(self, cli, test_files):
        """Test encoding with password provided as string"""
        cover_path, secret_files = test_files
        
        result = cli.encode_command(
            cover_path,
            secret_files,
            file_password="mypassword",
            show_stats=False
        )
        
        assert result == 0

    def test_encode_with_statistics(self, cli, test_files, monkeypatch):
        """Test encoding with statistics enabled"""
        cover_path, secret_files = test_files
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        result = cli.encode_command(
            cover_path,
            secret_files,
            file_password=None,
            show_stats=True
        )
        
        assert result == 0

    def test_encode_nonexistent_cover(self, cli):
        """Test encoding with nonexistent cover image"""
        with pytest.raises(FileNotFoundError):
            cli.encode_command(
            "nonexistent.png",
            ["secret.txt"],
            file_password=None,
            show_stats=False
        )

    def test_encode_multiple_secrets(self, cli, tmp_path, monkeypatch):
        """Test encoding multiple secret files"""
        cover = Image.new("RGB", (400, 400))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secrets = []
        for i in range(3):
            secret = tmp_path / f"secret{i}.txt"
            secret.write_text(f"Content {i}")
            secrets.append(str(secret))
        
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        result = cli.encode_command(
            str(cover_path),
            secrets,
            file_password=None,
            show_stats=False
        )
        
        assert result == 0


class TestDecodeCommand:
    """Test decode command functionality"""

    @pytest.fixture
    def cli(self):
        """Create CLI instance"""
        return ImageStegoCLI()

    @pytest.fixture
    def encoded_image(self, tmp_path, monkeypatch):
        """Create an encoded test image"""
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "secret.txt"
        secret.write_text("Secret data")
        
        coder = ImageMultiFormatCoder()
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        encode_dir = tmp_path / "encoded"
        stego_path = coder.encode(
            str(cover_path),
            [str(secret)],
            str(encode_dir),
            password=None,
            show_stats=False
        )
        
        return stego_path

    def test_decode_without_password(self, cli, encoded_image):
        """Test decoding without password"""
        result = cli.decode_command(
            encoded_image,
            "decoded",
            file_password=None
        )
        
        assert result == 0

        output_path = os.path.join("output", "decoded", "secret.txt")
        assert os.path.exists(output_path)

    def test_decode_with_password_string(self, cli, tmp_path, monkeypatch):
        """Test decoding with password provided as string"""
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "secret.txt"
        secret.write_text("Encrypted secret")
        
        coder = ImageMultiFormatCoder()
        encode_dir = tmp_path / "encoded"
        stego_path = coder.encode(
            str(cover_path),
            [str(secret)],
            str(encode_dir),
            password="testpass",
            show_stats=False
        )
        
        result = cli.decode_command(
            stego_path,
            "decoded_encrypted",
            file_password="testpass"
        )
        
        assert result == 0

    def test_decode_nonexistent_file(self, cli):
        """Test decoding nonexistent file"""

        with pytest.raises(FileNotFoundError, match="Cover image not found: nonexistent.png"):
            cli.decode_command(
            "nonexistent.png",
            "output",
            file_password='test'
        )
        

    def test_decode_clean_image(self, cli, tmp_path):
        """Test decoding image without hidden data"""
        clean_img = Image.new("RGB", (200, 200))
        clean_path = tmp_path / "clean.png"
        clean_img.save(clean_path)
        
        result = cli.decode_command(
            str(clean_path),
            "output",
            file_password=None
        )
        
        assert result == 0

    def test_decode_wrong_password(self, cli, tmp_path):
        """Test decoding with wrong password"""
        from ghostbit.imagestego.core.image_multiformat_coder import ImageMultiFormatCoder
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "secret.txt"
        secret.write_text("Data")
        
        coder = ImageMultiFormatCoder()
        encode_dir = tmp_path / "encoded"
        stego_path = coder.encode(
            str(cover_path),
            [str(secret)],
            str(encode_dir),
            password="correct",
            show_stats=False
        )
        
        result = cli.decode_command(
            stego_path,
            "output",
            file_password="wrong"
        )
        
        assert result == 0


class TestCapacityCommand:
    """Test capacity command functionality"""

    @pytest.fixture
    def cli(self):
        """Create CLI instance"""
        return ImageStegoCLI()

    def test_capacity_png(self, cli, tmp_path):
        """Test capacity calculation for PNG"""
        img = Image.new("RGB", (100, 100))
        path = tmp_path / "test.png"
        img.save(path)
        
        result = cli.capacity_command(str(path))
        
        assert result == 0

    def test_capacity_gif(self, cli, tmp_path):
        """Test capacity calculation for GIF"""
        img = Image.new("P", (100, 100))
        palette = list(range(256)) * 3
        img.putpalette(palette)
        path = tmp_path / "test.gif"
        img.save(path, format="GIF")
        
        result = cli.capacity_command(str(path))
        
        assert result == 0

    def test_capacity_svg(self, cli, tmp_path):
        """Test capacity calculation for SVG"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="0" y="0" width="100" height="100"/>
</svg>"""
        path = tmp_path / "test.svg"
        path.write_text(svg_content)
        
        result = cli.capacity_command(str(path))
        
        assert result == 0

    def test_capacity_nonexistent_file(self, cli):
        """Test capacity with nonexistent file"""
        with pytest.raises(FileNotFoundError):
            cli.capacity_command("nonexistent.png")

    def test_capacity_invalid_file(self, cli, tmp_path):
        """Test capacity with invalid file"""
        invalid = tmp_path / "invalid.txt"
        invalid.write_text("Not an image")

        with pytest.raises(ImageMultiFormatCoderException, match='File format not supported'):
            cli.capacity_command(str(invalid))
        


class TestAnalyzeCommand:
    """Test analyze command functionality"""

    @pytest.fixture
    def cli(self):
        """Create CLI instance"""
        return ImageStegoCLI()

    def test_analyze_clean_image(self, cli, tmp_path):
        """Test analyzing clean image"""
        img = Image.new("RGB", (200, 200))
        path = tmp_path / "clean.png"
        img.save(path)
        
        result = cli.analyze_command(str(path))
        
        assert result == 0

    def test_analyze_stego_image(self, cli, tmp_path, monkeypatch):
        """Test analyzing image with hidden data"""
        from ghostbit.imagestego.core.image_multiformat_coder import ImageMultiFormatCoder
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "secret.txt"
        secret.write_text("Hidden")
        
        coder = ImageMultiFormatCoder()
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        encode_dir = tmp_path / "encoded"
        stego_path = coder.encode(
            str(cover_path),
            [str(secret)],
            str(encode_dir),
            password=None,
            show_stats=False
        )
        
        result = cli.analyze_command(stego_path)
        
        assert result == 0

    def test_analyze_encrypted_image(self, cli, tmp_path):
        """Test analyzing encrypted image"""
        from ghostbit.imagestego.core.image_multiformat_coder import ImageMultiFormatCoder
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "secret.txt"
        secret.write_text("Encrypted data")
        
        coder = ImageMultiFormatCoder()
        encode_dir = tmp_path / "encoded"
        stego_path = coder.encode(
            str(cover_path),
            [str(secret)],
            str(encode_dir),
            password="password",
            show_stats=False
        )
        
        result = cli.analyze_command(stego_path)
        
        assert result == 0

    def test_analyze_gif(self, cli, tmp_path):
        """Test analyzing GIF"""
        img = Image.new('P', (300, 300))
        img.putpalette([i for i in range(256)] * 3)
        for x in range(300):
            for y in range(300):
                img.putpixel((x, y), (x + y) % 256)

        path = tmp_path / "test.gif"
        img.save(path, format="GIF")
        
        result = cli.analyze_command(str(path))
        
        assert result == 0

    def test_analyze_svg(self, cli, tmp_path):
        """Test analyzing SVG"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <circle cx="50" cy="50" r="40"/>
</svg>"""
        path = tmp_path / "test.svg"
        path.write_text(svg_content)
        
        result = cli.analyze_command(str(path))
        
        assert result == 0

    def test_analyze_nonexistent_file(self, cli):
        """Test analyzing nonexistent file"""
        with pytest.raises(FileNotFoundError):
            cli.analyze_command("nonexistent.png")


class TestExceptionHandling:
    """Test exception handling in CLI"""

    @pytest.fixture
    def cli(self):
        """Create CLI instance"""
        return ImageStegoCLI()

    @patch('ghostbit.imagestego.core.image_multiformat_coder.ImageMultiFormatCoder.encode')
    def test_encode_exception_handling(self, mock_encode, cli, tmp_path, monkeypatch):
        """Test exception handling in encode command"""
        from ghostbit.imagestego.core.image_multiformat_coder import ImageMultiFormatCoderException
        
        mock_encode.side_effect = ImageMultiFormatCoderException("Test error")
        
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "secret.txt"
        secret.write_text("Secret")
        
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        result = cli.encode_command(
            str(cover_path),
            [str(secret)],
            file_password=None,
            show_stats=False
        )
        
        assert result == 1

    @patch('ghostbit.imagestego.core.image_multiformat_coder.ImageMultiFormatCoder.decode')
    def test_decode_exception_handling(self, mock_decode, cli, tmp_path):
        """Test exception handling in decode command"""
        from ghostbit.imagestego.core.image_multiformat_coder import ImageMultiFormatCoderException
        
        mock_decode.side_effect = ImageMultiFormatCoderException("Test error")
        
        img = Image.new("RGB", (200, 200))
        img_path = tmp_path / "test.png"
        img.save(img_path)
        
        result = cli.decode_command(
            str(img_path),
            "output",
            file_password=None
        )
        
        assert result == 1


class TestOutputFormatting:
    """Test output formatting and headers"""

    @pytest.fixture
    def cli(self):
        """Create CLI instance"""
        return ImageStegoCLI()

    def test_print_header_with_emoji(self, cli, capsys):
        """Test print_header with emoji"""
        cli._print_header("Test Header", "🔒")
        
        captured = capsys.readouterr()
        assert "Test Header" in captured.out
        assert "🔒" in captured.out

    def test_print_header_without_emoji(self, cli, capsys):
        """Test print_header without emoji"""
        cli._print_header("Test Header", None)
        
        captured = capsys.readouterr()
        assert "Test Header" in captured.out


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def cli(self):
        """Create CLI instance"""
        return ImageStegoCLI()

    def test_encode_empty_secret_file(self, cli, tmp_path, monkeypatch):
        """Test encoding empty secret file"""
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "empty.txt"
        secret.write_text("")
        
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        result = cli.encode_command(
            str(cover_path),
            [str(secret)],
            file_password=None,
            show_stats=False
        )
        
        assert result == 0

    def test_encode_very_long_filename(self, cli, tmp_path, monkeypatch):
        """Test encoding file with very long name"""
        cover = Image.new("RGB", (200, 200))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        long_name = "a" * 100 + ".txt"
        secret = tmp_path / long_name
        secret.write_text("Content")
        
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        result = cli.encode_command(
            str(cover_path),
            [str(secret)],
            file_password=None,
            show_stats=False
        )
        
        assert result == 0

    def test_decode_to_nested_directory(self, cli, tmp_path, monkeypatch):
        """Test decoding to nested output directory"""
        from ghostbit.imagestego.core.image_multiformat_coder import ImageMultiFormatCoder
        
        cover = Image.new("RGB", (300, 300))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "secret.txt"
        secret.write_text("Data")
        
        coder = ImageMultiFormatCoder()
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        encode_dir = tmp_path / "encoded"
        stego_path = coder.encode(
            str(cover_path),
            [str(secret)],
            str(encode_dir),
            password=None,
            show_stats=False
        )
        
        nested_output = "output/level1/level2/decoded"
        result = cli.decode_command(
            stego_path,
            nested_output,
            file_password=None
        )
        
        assert result == 0


class TestPasswordValidation:
    """Test password validation and confirmation"""

    @pytest.fixture
    def cli(self):
        """Create CLI instance"""
        return ImageStegoCLI()


class TestCLIIntegration:
    """Test complete CLI workflows"""

    def test_full_encode_decode_workflow(self, tmp_path, monkeypatch):
        """Test complete encode and decode workflow via CLI"""
        cli = ImageStegoCLI()
        
        cover = Image.new("RGB", (400, 400))
        cover_path = tmp_path / "cover.png"
        cover.save(cover_path)
        
        secret = tmp_path / "secret.txt"
        secret_content = "Secret message for testing"
        secret.write_text(secret_content)
        
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        
        encode_result = cli.encode_command(
            str(cover_path),
            [str(secret)],
            file_password="test123",
            show_stats=True
        )
        assert encode_result == 0
        
        stego_path = os.path.join("output", "encoded", "cover_encoded.png")
        analyze_result = cli.analyze_command(stego_path)
        assert analyze_result == 0

        decode_result = cli.decode_command(
            stego_path,
            "decoded_full",
            file_password="test123"
        )
        assert decode_result == 0
        
        decoded_file = os.path.join("output", "decoded_full", "secret.txt")
        assert os.path.exists(decoded_file)
        with open(decoded_file) as f:
            assert f.read() == secret_content

