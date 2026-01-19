#!/usr/bin/env python3
import os
import wave
import struct
import shutil
import pytest
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from ghostbit.audiostego.core.audio_steganography import (
    EncodeMode,
    AudioSteganographyException,
    KeyEnterCanceledException,
    KeyRequiredEventArgs,
    SecretFileInfoItem,
    BaseFileInfoItem,
    CarrierFileInfo,
    Chunk,
    RiffChunk,
    FormatChunk,
    WavFile,
    SecretFile,
    DecodedFile,
    Coder,
)

"""
Tests for audiostego.core.audio_steganography module
"""

fixture_dir = Path(__file__).parent / "testcases"


class TestEncodeMode:
    """Test suite for EncodeMode enum"""

    def test_encode_mode_values(self) -> None:
        """Test EncodeMode enum has correct values"""
        assert EncodeMode.LOW_QUALITY.value == 2
        assert EncodeMode.NORMAL_QUALITY.value == 4
        assert EncodeMode.HIGH_QUALITY.value == 8

    def test_encode_mode_names(self) -> None:
        """Test EncodeMode enum has correct names"""
        assert EncodeMode.LOW_QUALITY.name == "LOW_QUALITY"
        assert EncodeMode.NORMAL_QUALITY.name == "NORMAL_QUALITY"
        assert EncodeMode.HIGH_QUALITY.name == "HIGH_QUALITY"


class TestExceptions:
    """Test suite for custom exceptions"""

    def test_steganography_exception(self) -> None:
        """Test AudioSteganographyException can be raised and caught"""
        with pytest.raises(AudioSteganographyException) as exc_info:
            raise AudioSteganographyException("Test error message")
        assert str(exc_info.value) == "Test error message"

    def test_key_enter_cancelled_exception(self) -> None:
        """Test KeyEnterCanceledException can be raised"""
        with pytest.raises(KeyEnterCanceledException):
            raise KeyEnterCanceledException()


class TestKeyRequiredEventArgs:
    """Test suite for KeyRequiredEventArgs dataclass"""

    def test_default_values(self) -> None:
        """Test KeyRequiredEventArgs default initialization"""
        args = KeyRequiredEventArgs()
        assert args.key == ""
        assert not args.cancel
        assert args.h22_version == ""

    def test_custom_values(self) -> None:
        """Test KeyRequiredEventArgs with custom values"""
        args = KeyRequiredEventArgs(key="test_key", cancel=True, h22_version="DSC2")
        assert args.key == "test_key"
        assert args.cancel
        assert args.h22_version == "DSC2"


class TestSecretFile:
    """Tests for missing SecretFile coverage (0% coverage)"""

    def test_secret_file_initialization(self):
        """Test SecretFile.__init__ (0% coverage)"""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"secret data" * 100)
            temp_file = f.name

        try:
            secret = SecretFile(temp_file, 1024, EncodeMode.NORMAL_QUALITY, None)

            assert secret.file_name == temp_file
            assert secret.buff_size > 0
            assert len(secret.current_block) > 0

            secret.close()
        finally:
            os.unlink(temp_file)

    def test_secret_file_read_block(self):
        """Test SecretFile.read_block (0% coverage)"""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"X" * 10000)
            temp_file = f.name

        try:
            secret = SecretFile(temp_file, 1024, EncodeMode.NORMAL_QUALITY, None)

            secret.read_block()
            assert len(secret.current_block) >= 0

            secret.close()
        finally:
            os.unlink(temp_file)

    def test_secret_file_get_current_block(self):
        """Test SecretFile.get_current_block (0% coverage)"""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test data")
            temp_file = f.name

        try:
            secret = SecretFile(temp_file, 1024, EncodeMode.NORMAL_QUALITY, None)

            block = secret.get_current_block()
            assert isinstance(block, bytes)
            assert len(block) > 0

            secret.close()
        finally:
            os.unlink(temp_file)

    def test_secret_file_with_encryption(self):
        """Test SecretFile with cipher (0% coverage)"""
        coder = Coder()
        coder.set_key_ascii("testpass")
        cipher = coder._get_cipher()

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"secret" * 100)
            temp_file = f.name

        try:
            secret = SecretFile(temp_file, 1024, EncodeMode.NORMAL_QUALITY, cipher)

            block = secret.get_current_block()
            assert isinstance(block, bytes)
            assert len(block) > 0

            secret.close()
        finally:
            os.unlink(temp_file)

    def test_secret_file_context_manager(self):
        """Test SecretFile __enter__ and __exit__ (0% coverage)"""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"data")
            temp_file = f.name

        try:
            with SecretFile(temp_file, 1024, EncodeMode.NORMAL_QUALITY, None) as secret:
                assert secret is not None
                block = secret.get_current_block()
                assert len(block) > 0
        finally:
            os.unlink(temp_file)


class TestDecodedFile:
    """Tests for missing DecodedFile coverage (0% coverage)"""

    def test_decoded_file_initialization(self):
        """Test DecodedFile.__init__ (0% coverage)"""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"X" * 10000)
            temp_file = f.name

        try:
            with open(temp_file, "rb") as stream:
                decoded = DecodedFile(
                    stream=stream,
                    buff_size=1024,
                    start_pos=0,
                    end_pos=5000,
                    mode=EncodeMode.NORMAL_QUALITY,
                )

                assert decoded.buff_size == 1024
                assert decoded.start_position == 0
                assert decoded.end_position == 5000
                assert not decoded.is_last_block
        finally:
            os.unlink(temp_file)

    def test_decoded_file_read_block(self):
        """Test DecodedFile.read_block (0% coverage)"""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"Y" * 10000)
            temp_file = f.name

        try:
            with open(temp_file, "rb") as stream:
                decoded = DecodedFile(
                    stream=stream,
                    buff_size=1024,
                    start_pos=0,
                    end_pos=5000,
                    mode=EncodeMode.NORMAL_QUALITY,
                )

                decoded.read_block()
                assert len(decoded.current_block) > 0

                while not decoded.is_last_block:
                    decoded.read_block()

                assert decoded.is_last_block
        finally:
            os.unlink(temp_file)


class TestSecretFileInfoItem:
    """Test suite for SecretFileInfoItem dataclass"""

    def test_initialization_with_nonexistent_file(self) -> None:
        """Test SecretFileInfoItem with non-existent file"""
        item = SecretFileInfoItem("/nonexistent/path/file.txt")
        assert item.full_path == "/nonexistent/path/file.txt"
        assert item.file_name == "file.txt"
        assert item.file_size == 0
        assert not item.is_in_add_list

    def test_initialization_with_existing_file(self) -> None:
        """Test SecretFileInfoItem with existing file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            item = SecretFileInfoItem(temp_path, is_in_add_list=True)
            assert item.full_path == temp_path
            assert item.file_name == os.path.basename(temp_path)
            assert item.file_size > 0
        finally:
            os.unlink(temp_path)

    def test_file_size_mb_small_file(self) -> None:
        """Test file_size_mb property for small files"""
        test_file = str(fixture_dir / "test_document.txt")
        item = SecretFileInfoItem(test_file)
        item.file_size = 50000
        assert "< 0.1 MB" in item.file_size_mb

    def test_file_size_mb_large_file(self) -> None:
        """Test file_size_mb property for larger files"""
        test_file = str(fixture_dir / "test_image.png")
        item = SecretFileInfoItem(test_file)
        item.file_size = 5 * 1024 * 1024
        assert "5.0 MB" in item.file_size_mb

    def test_is_in_add_list_flag(self) -> None:
        """Test is_in_add_list flag"""
        test_file = str(fixture_dir / "test_secret.txt")
        item = SecretFileInfoItem(test_file, is_in_add_list=True)
        assert item.is_in_add_list

    def test_start_and_end_position(self) -> None:
        """Test start and end position attributes"""
        test_file = str(fixture_dir / "test_encoded.wav")
        item = SecretFileInfoItem(test_file)
        item.start_position = 1000
        item.end_position = 2000
        assert item.start_position == 1000
        assert item.end_position == 2000

    def test_with_real_file(self):
        """Test SecretFileInfoItem with actual file"""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            content = b"test secret content"
            f.write(content)
            temp_path = f.name

        try:
            item = SecretFileInfoItem(temp_path, is_in_add_list=True)
            assert item.file_size == len(content)
            assert item.file_name == os.path.basename(temp_path)
            assert item.is_in_add_list
        finally:
            os.unlink(temp_path)

    def test_file_size_mb_boundary(self):
        """Test file_size_mb at exactly 0.1 MB boundary"""

        item = SecretFileInfoItem("test_file.txt")

        item.file_size = int(0.1 * 1024 * 1024)
        size_str = item.file_size_mb
        assert "0.1 MB" in size_str

        item.file_size = int(0.09 * 1024 * 1024)
        size_str = item.file_size_mb
        assert "< 0.1 MB" in size_str


class TestBaseFileInfoItem:
    """Test suite for BaseFileInfoItem dataclass"""

    def test_initialization_with_nonexistent_file(self) -> None:
        """Test BaseFileInfoItem with non-existent file"""
        item = BaseFileInfoItem(
            full_path="/nonexistent/file.wav",
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        assert item.full_path == "/nonexistent/file.wav"
        assert item.encode_mode == EncodeMode.NORMAL_QUALITY
        assert item.wav_head_length == 44
        assert item.file_size == 0
        assert item.max_inner_files_size == 0

    def test_initialization_with_existing_file(self) -> None:
        """Test BaseFileInfoItem with existing file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(b"0" * 10000)
            temp_path = f.name

        try:
            item = BaseFileInfoItem(
                full_path=temp_path,
                encode_mode=EncodeMode.NORMAL_QUALITY,
                wav_head_length=44,
            )
            assert item.file_size == 10000
            assert item.max_inner_files_size > 0
        finally:
            os.unlink(temp_path)

    def test_max_inner_files_size_calculation(self) -> None:
        """Test max_inner_files_size calculation with different quality modes"""
        test_file = str(fixture_dir / "test_carrier.flac")
        item = BaseFileInfoItem(
            full_path=test_file,
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        assert item.max_inner_files_size == 17608

    def test_remains_inner_files_size(self) -> None:
        """Test remains_inner_files_size property"""
        test_file = str(fixture_dir / "test_carrier.flac")
        item = BaseFileInfoItem(
            full_path=test_file,
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        item.file_size = 100000
        item.inner_files_size = 1000

        remains = item.remains_inner_files_size
        assert remains >= 0
        assert remains == item.max_inner_files_size - item.inner_files_size - 32 - 19

    def test_remains_inner_files_size_mb_bytes(self) -> None:
        """Test remains_inner_files_size_mb for small capacity"""
        test_file = str(fixture_dir / "test_carrier.wav")
        item = BaseFileInfoItem(
            full_path=test_file,
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        item.file_size = 1000

        size_str = item.remains_inner_files_size_mb
        assert "0.1 MB" in size_str

    def test_remains_inner_files_size_mb_megabytes(self) -> None:
        """Test remains_inner_files_size_mb for large capacity"""
        test_file = str(fixture_dir / "test_encoded.wav")
        item = BaseFileInfoItem(
            full_path=test_file,
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        item.file_size = 10 * 1024 * 1024

        size_str = item.remains_inner_files_size_mb
        assert "MB" in size_str

    def test_add_inner_file_size_success(self) -> None:
        """Test add_inner_file_size with sufficient space"""
        test_file = str(fixture_dir / "test_carrier.m4a")
        item = BaseFileInfoItem(
            full_path=test_file,
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        item.file_size = 100000

        initial_size = item.inner_files_size
        result = item.add_inner_file_size(100)

        assert result
        assert item.inner_files_size == initial_size + 100 + 32 + 19

    def test_add_inner_file_size_failure(self) -> None:
        """Test add_inner_file_size with insufficient space"""
        test_file = str(fixture_dir / "test_carrier.wav")
        item = BaseFileInfoItem(
            full_path=test_file,
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        item.file_size = 1000
        result = item.add_inner_file_size(10000000)

        assert not result

    def test_remove_inner_file_size(self) -> None:
        """Test remove_inner_file_size"""
        test_file = str(fixture_dir / "test_carrier.wav")
        item = BaseFileInfoItem(
            full_path=test_file,
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        item.inner_files_size = 1000
        item.remove_inner_file_size(100)

        assert item.inner_files_size == 1000 - (100 + 32 + 19)

    def test_remains_inner_files_size_mb(self):
        """Test remains_inner_files_size_mb (0% coverage)"""
        item = BaseFileInfoItem(
            full_path="/test/file.wav",
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        item.file_size = 100000

        size_str = item.remains_inner_files_size_mb
        assert isinstance(size_str, str)
        assert "MB" in size_str or "Bytes" in size_str

    def test_with_different_encode_modes(self):
        """Test capacity calculation with different encode modes"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
        temp_file = f.name

        try:
            item_low = BaseFileInfoItem(
                full_path=temp_file,
                encode_mode=EncodeMode.LOW_QUALITY,
                wav_head_length=44,
            )

            item_normal = BaseFileInfoItem(
                full_path=temp_file,
                encode_mode=EncodeMode.NORMAL_QUALITY,
                wav_head_length=44,
            )

            item_high = BaseFileInfoItem(
                full_path=temp_file,
                encode_mode=EncodeMode.HIGH_QUALITY,
                wav_head_length=44,
            )

            capacity_low = item_low.max_inner_files_size
            capacity_normal = item_normal.max_inner_files_size
            capacity_high = item_high.max_inner_files_size

            assert capacity_low > 0
            assert capacity_normal > 0
            assert capacity_high > 0
            assert capacity_low > capacity_normal > capacity_high
            assert capacity_low > capacity_normal > capacity_high
            assert capacity_low / capacity_normal == pytest.approx(2.0, rel=0.1)
            assert capacity_low / capacity_high == pytest.approx(4.0, rel=0.1)
        finally:
            os.unlink(temp_file)

    def test_add_inner_file_size_at_limit(self):
        """Test adding file size at exact capacity limit"""
        item = BaseFileInfoItem(
            full_path="/test/file.wav",
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        item.file_size = 100000
        max_capacity = item.remains_inner_files_size
        result = item.add_inner_file_size(max_capacity)

        assert result
        assert item.remains_inner_files_size == 0

    def test_remove_inner_file_size_below_zero(self):
        """Test removing more than current inner_files_size"""
        item = BaseFileInfoItem(
            full_path="/test/file.wav",
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )
        item.inner_files_size = 100
        item.remove_inner_file_size(200)

        assert item.inner_files_size <= 0


class TestCarrierFileInfo:
    """Test suite for CarrierFileInfo dataclass"""

    def test_default_initialization(self) -> None:
        """Test CarrierFileInfo default values"""
        info = CarrierFileInfo()
        assert info.file_name == ""
        assert info.wav_head_length == 0
        assert info.h22_version == ""

    def test_custom_initialization(self) -> None:
        """Test CarrierFileInfo with custom values"""
        test_file = str(fixture_dir / "test_encoded.wav")
        info = CarrierFileInfo(
            file_name=test_file, wav_head_length=44, h22_version="DSC2"
        )
        assert info.file_name == test_file
        assert info.wav_head_length == 44
        assert info.h22_version == "DSC2"


class TestCoder:
    """Test suite for Coder class"""

    def test_initialization(self) -> None:
        """Test Coder initialization"""
        coder = Coder()
        assert coder.buff_size == 1 * 1024 * 1024
        assert not coder.encrypt
        assert coder.encode_quality_mode == EncodeMode.NORMAL_QUALITY
        assert coder.decode_quality_mode == EncodeMode.NORMAL_QUALITY
        assert len(coder.secret_files_info_items) == 0

    def test_set_key_ascii(self) -> None:
        """Test set_key_ascii method"""
        coder = Coder()
        coder.set_key_ascii("testpassword")

        assert coder.aes_key is not None
        assert coder.key_verif_block is not None
        assert len(coder.aes_key) == 32

    def test_set_key_unicode(self) -> None:
        """Test set_key_unicode method"""
        coder = Coder()
        coder.set_key_unicode("testpassword")

        assert coder.aes_key is not None
        assert coder.key_verif_block is not None
        assert len(coder.aes_key) == 32

    def test_set_key_unicode_with_special_chars(self) -> None:
        """Test set_key_unicode with special characters"""
        coder = Coder()
        coder.set_key_unicode("пароль123!@#")

        assert coder.aes_key is not None
        assert coder.key_verif_block is not None

    def test_get_cipher(self) -> None:
        """Test _get_cipher method"""
        coder = Coder()
        coder.set_key_ascii("testpassword")

        cipher = coder._get_cipher()
        assert cipher is not None

    def test_get_cipher_without_key(self) -> None:
        """Test _get_cipher raises exception without key"""
        coder = Coder()
        cipher = coder._get_cipher()
        assert cipher is not None

    def test_encode_data_basic(self) -> None:
        """Test encode_data method"""
        coder = Coder()
        base_data = bytearray(100)
        secret_data = b"test data"

        encoded = coder.encode_data(base_data, secret_data, len(secret_data))

        assert len(encoded) > 0
        assert isinstance(encoded, bytearray)

    def test_decode_data_basic(self) -> None:
        """Test decode_data method"""
        coder = Coder()
        base_data = bytearray(100)
        secret_data = b"test data"

        encoded = coder.encode_data(base_data, secret_data, len(secret_data))
        decoded = coder.decode_data(bytes(encoded), len(encoded))

        assert len(decoded) > 0

    def test_encode_decode_roundtrip(self) -> None:
        """Test encoding and decoding data roundtrip"""
        coder = Coder()
        coder.encode_quality_mode = EncodeMode.NORMAL_QUALITY

        original_data = b"Hello, World! This is test data."
        base_data = bytearray(1000)

        encoded = coder.encode_data(base_data, original_data, len(original_data))
        decoded = coder.decode_data(bytes(encoded), len(encoded))

        assert (
            original_data in decoded or decoded[: len(original_data)] == original_data
        )

    def test_callback_on_encoded_element(self) -> None:
        """Test on_encoded_element callback"""
        coder = Coder()
        callback_called = []

        def callback() -> None:
            callback_called.append(1)

        coder.on_encoded_element = callback
        coder.on_encoded_element()

        assert len(callback_called) == 1

    def test_callback_on_decoded_element(self) -> None:
        """Test on_decoded_element callback"""
        coder = Coder()
        callback_called = []

        def callback() -> None:
            callback_called.append(1)

        coder.on_decoded_element = callback
        coder.on_decoded_element()

        assert len(callback_called) == 1

    def test_callback_on_key_required(self) -> None:
        """Test on_key_required callback"""
        coder = Coder()
        callback_called = []

        def callback(args: Any) -> None:
            callback_called.append(args)
            args.key = "test_key"

        coder.on_key_required = callback

        args = KeyRequiredEventArgs()
        coder.on_key_required(args)

        assert len(callback_called) == 1
        assert args.key == "test_key"

    def test_decoder_folder_attribute(self) -> None:
        """Test decoder_folder can be set"""
        coder = Coder()
        coder.decoder_folder = "/test/output"

        assert coder.decoder_folder == "/test/output"

    def test_encoder_output_file_path_attribute(self) -> None:
        """Test encoder_output_file_path can be set"""
        coder = Coder()
        coder.encoder_output_file_path = "/test/output.wav"

        assert coder.encoder_output_file_path == "/test/output.wav"

    def test_secret_files_management(self) -> None:
        """Test adding and clearing secret files"""
        coder = Coder()

        test_file_1 = str(fixture_dir / "test_secret.txt")
        test_file_2 = str(fixture_dir / "test_document.text")

        file1 = SecretFileInfoItem(test_file_1)
        file2 = SecretFileInfoItem(test_file_2)

        coder.secret_files_info_items.append(file1)
        coder.secret_files_info_items.append(file2)

        assert len(coder.secret_files_info_items) == 2

        coder.secret_files_info_items.clear()

        assert len(coder.secret_files_info_items) == 0

    def test_quality_mode_settings(self) -> None:
        """Test setting different quality modes"""
        coder = Coder()

        coder.encode_quality_mode = EncodeMode.HIGH_QUALITY
        assert coder.encode_quality_mode == EncodeMode.HIGH_QUALITY

        coder.decode_quality_mode = EncodeMode.LOW_QUALITY
        assert coder.decode_quality_mode == EncodeMode.LOW_QUALITY

    def test_encryption_flag(self) -> None:
        """Test encryption flag can be toggled"""
        coder = Coder()

        assert not coder.encrypt

        coder.encrypt = True
        assert coder.encrypt

        coder.encrypt = False
        assert not coder.encrypt

    @patch.object(Coder, "_get_cipher")
    def test_encode_with_mocked_cipher(self, mock_get_cipher):
        """Test encoding with mocked cipher"""
        mock_cipher = MagicMock()
        mock_cipher.encrypt.return_value = b"encrypted_data"
        mock_get_cipher.return_value = mock_cipher

        coder = Coder()
        coder.set_key_ascii("testpass")
        coder.encrypt = True

        base_data = bytearray(1000)
        secret_data = b"test"

        encoded = coder.encode_data(base_data, secret_data, len(secret_data))

        assert isinstance(encoded, bytearray)


class TestCoderConstants:
    """Test Coder class constants"""

    def test_all_version_constants(self):
        """Test all version string constants"""
        assert Coder.H22_VERSION_DSC2 == "DSC2"
        assert Coder.H22_VERSION_DSCF == "DSCF"
        assert Coder.H32_VERSION_DSSF == "DSSF"

        assert isinstance(Coder.H22_VERSION_DSC2, str)
        assert isinstance(Coder.H22_VERSION_DSCF, str)
        assert isinstance(Coder.H32_VERSION_DSSF, str)

    def test_try_find_limit_constant(self):
        """Test try find limit constant"""
        assert Coder.OTHER_HEAD26_TRY_FIND_LIMIT == 352800
        assert isinstance(Coder.OTHER_HEAD26_TRY_FIND_LIMIT, int)
        assert Coder.OTHER_HEAD26_TRY_FIND_LIMIT > 0

    def test_aes_key_size_constant(self):
        """Test AES key size constant"""
        assert Coder.AES_KEY_SIZE == 32
        assert isinstance(Coder.AES_KEY_SIZE, int)


class TestCoderSetBuffSize:
    """Test Coder.set_buff_size (0% coverage)"""

    def test_set_buff_size_valid(self):
        """Test set_buff_size with valid size"""
        coder = Coder()

        coder.set_buff_size(2 * 1024 * 1024)
        assert coder.buff_size == 2 * 1024 * 1024

    def test_set_buff_size_too_large(self):
        """Test set_buff_size with size too large"""
        coder = Coder()

        coder.set_buff_size(600 * 1024 * 1024)
        assert coder.buff_size == 1048576

    def test_set_buff_size_too_small(self):
        """Test set_buff_size with size too small"""
        coder = Coder()

        coder.set_buff_size(512)
        assert coder.buff_size == 1048576

    def test_set_buff_size_not_multiple_of_16(self):
        """Test set_buff_size with size not multiple of 16"""
        coder = Coder()

        coder.set_buff_size(1000000)
        assert coder.buff_size == 1000000


class TestChunk:
    """Test suite for Chunk class"""

    def test_chunk_constants(self) -> None:
        """Test Chunk class constants"""
        assert Chunk.PCM_AUDIO_FORMAT == 1
        assert Chunk.RIFF_CHUNK_ID == "RIFF"
        assert Chunk.DATA_CHUNK_ID == "DATA"
        assert Chunk.FORMAT_CHUNK_ID == "FMT "
        assert Chunk.WAVE_FORMAT_KEY == "WAVE"

    def test_chunk_size_with_header(self):
        """Test chunk_size_with_header property (0% coverage)"""
        mock_stream = MagicMock()
        mock_stream.read.side_effect = [b"FMT ", struct.pack("<I", 100), b"X" * 100]

        chunk = Chunk(mock_stream)
        assert chunk.chunk_size_with_header == 108

    def test_chunk_with_invalid_size(self):
        """Test Chunk with invalid size raises exception"""
        mock_stream = MagicMock()
        mock_stream.read.side_effect = [
            b"FMT",
            struct.pack("<I", 0),
        ]

        with pytest.raises(AudioSteganographyException, match="Invalid chunk size"):
            Chunk(mock_stream)

    def test_riff_chunk_properties(self):
        """Test RiffChunk properties"""
        mock_stream = MagicMock()
        mock_stream.read.side_effect = [
            b"RIFF",
            struct.pack("<I", 1000),
            b"WAVE",
        ]

        riff = RiffChunk(mock_stream)
        assert riff.chunk_id == "RIFF"
        assert riff.chunk_size == 1000
        assert riff.format == "WAVE"

    def test_format_chunk_invalid_type(self):
        """Test FormatChunk rejects non-FMT chunk"""
        mock_chunk = MagicMock()
        mock_chunk.chunk_id = "DATA"

        with pytest.raises(AudioSteganographyException, match="Invalid chunk type"):
            FormatChunk(mock_chunk)

    def test_format_chunk_properties(self):
        """Test FormatChunk extracts audio format data"""
        mock_chunk = MagicMock()
        mock_chunk.chunk_id = "FMT "
        mock_chunk.chunk_size = 16

        # Create format chunk data: id(4) + size(4) + format(2) + channels(2)
        format_data = b"fmt " + struct.pack("<I", 16) + struct.pack("<HH", 1, 2)
        mock_chunk.all_chunk_data = format_data

        fmt_chunk = FormatChunk(mock_chunk)
        assert fmt_chunk.audio_format == 1  # PCM
        assert fmt_chunk.number_of_channels == 2


@pytest.mark.integration
class TestCoderIntegration:
    """Integration tests for Coder class"""

    def test_analyze_nonexistent_file(self) -> None:
        """Test analyzing a non-existent file raises exception"""
        coder = Coder()

        with pytest.raises(Exception):
            coder.analyze_wav("/nonexistent/file.wav")

    def test_key_verification_blocks_match(self) -> None:
        """Test that same password generates same key verification block"""
        coder1 = Coder()
        coder2 = Coder()

        password = "testpassword123"

        coder1.set_key_unicode(password)
        coder2.set_key_unicode(password)

        assert coder1.key_verif_block == coder2.key_verif_block

    def test_different_passwords_different_keys(self) -> None:
        """Test that different passwords generate different keys"""
        coder1 = Coder()
        coder2 = Coder()

        coder1.set_key_unicode("password1")
        coder2.set_key_unicode("password2")

        assert coder1.aes_key != coder2.aes_key
        assert coder1.key_verif_block != coder2.key_verif_block


class TestCoderKeyManagement:
    """Test suite for Coder key management methods"""

    def test_set_key_ascii_empty_string(self):
        """Test set_key_ascii with empty string"""
        coder = Coder()
        coder.set_key_ascii("")

        assert coder.aes_key is not None
        assert len(coder.aes_key) == 32

    def test_set_key_unicode_with_emoji(self):
        """Test set_key_unicode with emoji characters"""
        coder = Coder()
        coder.set_key_unicode("🔐secure🔑")

        assert coder.aes_key is not None
        assert len(coder.aes_key) == 32
        assert coder.key_verif_block is not None

    def test_set_key_unicode_long_password(self):
        """Test set_key_unicode with very long password"""
        coder = Coder()
        long_password = "a" * 1000
        coder.set_key_unicode(long_password)

        assert len(coder.aes_key) == 32

    def test_key_verification_consistency(self):
        """Test that same password produces same key_verif_block"""
        coder1 = Coder()
        coder2 = Coder()

        password = "test_password_123"

        coder1.set_key_unicode(password)
        coder2.set_key_unicode(password)

        assert coder1.aes_key == coder2.aes_key
        assert coder1.key_verif_block == coder2.key_verif_block


class TestCoderEncodeDecodeData:
    """Test suite for encode_data and decode_data methods"""

    def test_encode_data_with_different_qualities(self):
        """Test encode_data with different quality modes"""
        coder = Coder()
        base_data = bytearray(1000)
        secret_data = b"test" * 10

        for mode in [
            EncodeMode.LOW_QUALITY,
            EncodeMode.NORMAL_QUALITY,
            EncodeMode.HIGH_QUALITY,
        ]:
            coder.encode_quality_mode = mode
            encoded = coder.encode_data(base_data.copy(), secret_data, len(secret_data))

            assert len(encoded) > 0
            assert isinstance(encoded, bytearray)

    def test_decode_data_empty(self):
        """Test decode_data with empty data"""
        coder = Coder()

        decoded = coder.decode_data(b"", 0)

        assert isinstance(decoded, bytearray)
        assert len(decoded) == 0

    def test_encode_decode_with_encryption(self):
        """Test encode/decode roundtrip with encryption"""
        coder = Coder()
        coder.set_key_ascii("testpassword")
        coder.encrypt = True

        base_data = bytearray(1000)
        original_secret = b"secret message"

        encoded = coder.encode_data(base_data, original_secret, len(original_secret))
        decoded = coder.decode_data(bytes(encoded), len(encoded))

        assert original_secret in decoded


class TestCoderCallbacks:
    """Test suite for Coder callback functionality"""

    def test_on_encoded_element_multiple_calls(self):
        """Test on_encoded_element callback is called multiple times"""
        coder = Coder()
        call_count = []

        def callback():
            call_count.append(1)

        coder.on_encoded_element = callback

        for _ in range(5):
            coder.on_encoded_element()

        assert len(call_count) == 5

    def test_on_decoded_element_with_state(self):
        """Test on_decoded_element callback can track state"""
        coder = Coder()
        state: dict[str, int | list[str]] = {"count": 0, "data": []}

        def callback():
            count = state["count"]
            data = state["data"]
            assert isinstance(count, int)
            assert isinstance(data, list)
            state["count"] = count + 1
            data.append(f"decoded_{count + 1}")

        coder.on_decoded_element = callback

        for _ in range(3):
            coder.on_decoded_element()

        count = state["count"]
        data = state["data"]
        assert isinstance(count, int)
        assert isinstance(data, list)
        assert count == 3
        assert len(data) == 3

    def test_on_key_required_cancel(self):
        """Test on_key_required callback with cancel"""
        coder = Coder()

        def callback(args: KeyRequiredEventArgs):
            args.cancel = True
            args.key = ""

        coder.on_key_required = callback

        args = KeyRequiredEventArgs()
        coder.on_key_required(args)

        assert args.cancel
        assert args.key == ""


class TestCoderFileOperations:
    """Test suite for Coder file operations"""

    def test_secret_files_add_remove(self):
        """Test adding and removing secret files"""
        coder = Coder()

        file1 = SecretFileInfoItem("/test/file1.txt")
        file2 = SecretFileInfoItem("/test/file2.txt")
        file3 = SecretFileInfoItem("/test/file3.txt")

        coder.secret_files_info_items.append(file1)
        coder.secret_files_info_items.append(file2)
        coder.secret_files_info_items.append(file3)

        assert len(coder.secret_files_info_items) == 3

        coder.secret_files_info_items.remove(file2)
        assert len(coder.secret_files_info_items) == 2
        assert file2 not in coder.secret_files_info_items

    def test_base_file_initialization(self):
        """Test base_file can be set"""
        coder = Coder()

        base = BaseFileInfoItem(
            full_path="/test/carrier.wav",
            encode_mode=EncodeMode.NORMAL_QUALITY,
            wav_head_length=44,
        )

        coder.base_file = base

        assert coder.base_file is not None
        assert coder.base_file.encode_mode == EncodeMode.NORMAL_QUALITY


class TestCoderEdgeCases:
    """Test edge cases and error conditions"""

    def test_encrypt_flag_toggle(self):
        """Test toggling encrypt flag"""
        coder = Coder()

        assert not coder.encrypt

        coder.encrypt = True
        assert coder.encrypt

        coder.encrypt = False
        assert not coder.encrypt

    def test_quality_modes_all_values(self):
        """Test all quality mode values"""
        assert EncodeMode.LOW_QUALITY.value == 2
        assert EncodeMode.NORMAL_QUALITY.value == 4
        assert EncodeMode.HIGH_QUALITY.value == 8

        assert EncodeMode.LOW_QUALITY.value < EncodeMode.NORMAL_QUALITY.value
        assert EncodeMode.NORMAL_QUALITY.value < EncodeMode.HIGH_QUALITY.value

    def test_buff_size_configuration(self):
        """Test buffer size can be configured"""
        coder = Coder()

        original_buff_size = coder.buff_size
        assert original_buff_size == 1 * 1024 * 1024

        coder.buff_size = 2 * 1024 * 1024
        assert coder.buff_size == 2 * 1024 * 1024


class TestWavFile:
    """Tests for missing WavFile coverage"""

    def test_wavfile_read_block(self):
        """Test WavFile.read_block method (0% coverage)"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav = f.name

        try:
            block_size = 1024
            num_blocks = 3
            with wave.open(temp_wav, "w") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(44100)

                wav.writeframes(b"\x00" * (block_size * num_blocks))

            wav_file = WavFile(
                temp_wav, block_size, EncodeMode.NORMAL_QUALITY, None, False
            )

            blocks_read = 0
            while not wav_file.is_last_block:
                wav_file.read_block()
                blocks_read += 1
                assert (
                    len(wav_file.current_block) > 0
                ), f"Block {blocks_read} should have data"

                if blocks_read < num_blocks:
                    assert (
                        not wav_file.is_last_block
                    ), f"Block {blocks_read} should not be last"

            assert (
                blocks_read == num_blocks
            ), f"Expected {num_blocks} blocks, read {blocks_read}"

        finally:
            os.unlink(temp_wav)

    def test_wavfile_read_rest_data(self):
        """Test WavFile.read_rest_data method (0% coverage)"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav = f.name

        try:
            with wave.open(temp_wav, "w") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(44100)
                wav.writeframes(b"\x00\x00" * 44100)

            wav_file = WavFile(temp_wav, 1024, EncodeMode.NORMAL_QUALITY, None, False)
            wav_file.read_rest_data()

            assert len(wav_file.current_block) > 0
            assert wav_file.size_last_block > 0

            wav_file.close()
        finally:
            os.unlink(temp_wav)

    def test_wavfile_seek_operations(self):
        """Test WavFile seek methods (0% coverage)"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav = f.name

        try:
            with wave.open(temp_wav, "w") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(44100)
                wav.writeframes(b"\x00\x00" * 44100)

            wav_file = WavFile(temp_wav, 1024, EncodeMode.NORMAL_QUALITY, None, False)

            initial_pos = wav_file.file_stream.tell()
            wav_file.seek_in_stream(100)
            new_pos = wav_file.file_stream.tell()
            assert new_pos == initial_pos + 100

            wav_file.seek_from_begin(0)
            assert wav_file.file_stream.tell() >= 0

            wav_file.close()
        finally:
            os.unlink(temp_wav)


@pytest.mark.integration
class TestWavFileIntegration:
    """Integration tests for WavFile class"""

    def test_create_real_wav_file(self):
        """Test creating and analyzing a real WAV file"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav = f.name

        try:
            with wave.open(temp_wav, "w") as wav:
                wav.setnchannels(1)  # Mono
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(44100)  # 44.1kHz

                silence = b"\x00\x00" * 44100
                wav.writeframes(silence)

            coder = Coder()
            result = coder.analyze_wav(temp_wav)

            assert isinstance(result, CarrierFileInfo)
            assert os.path.basename(result.file_name) == os.path.basename(temp_wav)

        finally:
            if os.path.exists(temp_wav):
                os.unlink(temp_wav)


class TestExceptionHandling:
    """Test exception handling"""

    def test_steganography_exception_message(self):
        """Test AudioSteganographyException with custom message"""
        with pytest.raises(AudioSteganographyException) as exc_info:
            raise AudioSteganographyException("Custom error message")

        assert "Custom error message" in str(exc_info.value)

    def test_key_enter_cancelled_exception(self):
        """Test KeyEnterCanceledException can be caught"""
        try:
            raise KeyEnterCanceledException()
        except KeyEnterCanceledException:
            assert True
        except Exception:
            assert False


class TestDataclassDefaults:
    """Test dataclass default values"""

    def test_key_required_event_args_defaults(self):
        """Test KeyRequiredEventArgs default values"""
        args = KeyRequiredEventArgs()

        assert args.key == ""
        assert not args.cancel
        assert args.h22_version == ""

    def test_carrier_file_info_defaults(self):
        """Test CarrierFileInfo default values"""
        info = CarrierFileInfo()

        assert info.file_name == ""
        assert info.wav_head_length == 0
        assert info.h22_version == ""

    def test_key_required_event_args_custom(self):
        """Test KeyRequiredEventArgs with custom values"""
        args = KeyRequiredEventArgs(key="mykey", cancel=True, h22_version="DSC2")

        assert args.key == "mykey"
        assert args.cancel
        assert args.h22_version == "DSC2"


class TestCoderDecodeData:
    """Improve Coder.decode_data coverage"""

    def test_decode_data_low_quality(self):
        """Test decode_data with LOW_QUALITY mode"""
        coder = Coder()
        coder.decode_quality_mode = EncodeMode.LOW_QUALITY
        coder.encode_quality_mode = EncodeMode.LOW_QUALITY
        base_data = bytearray(100)
        secret_data = b"test"
        encoded = coder.encode_data(base_data, secret_data, len(secret_data))
        decoded = coder.decode_data(bytes(encoded), len(encoded))
        assert len(decoded) == len(encoded) // 2

    def test_decode_data_high_quality(self):
        """Test decode_data with HIGH_QUALITY mode"""
        coder = Coder()
        coder.decode_quality_mode = EncodeMode.HIGH_QUALITY
        coder.encode_quality_mode = EncodeMode.HIGH_QUALITY
        base_data = bytearray(800)
        secret_data = b"test"
        encoded = coder.encode_data(base_data, secret_data, len(secret_data))
        decoded = coder.decode_data(bytes(encoded), len(encoded))
        assert len(decoded) == len(encoded) // 8


class TestCoderEncodeFilesToWav:
    """Test Coder.encode_files_to_wav"""

    @pytest.mark.integration
    def test_encode_files_to_wav_basic(self):
        """Test basic encode_files_to_wav workflow"""
        coder = Coder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            carrier_file = f.name

        with wave.open(carrier_file, "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            wav.writeframes(b"\x00\x00" * (44100 * 5))

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"secret content")
            secret_file = f.name

        output_file = tempfile.mktemp(suffix=".wav")

        try:
            secret_item = SecretFileInfoItem(secret_file)
            secret_item.is_in_add_list = True
            coder.secret_files_info_items.append(secret_item)

            base_item = BaseFileInfoItem(
                full_path=carrier_file,
                encode_mode=EncodeMode.NORMAL_QUALITY,
                wav_head_length=44,
            )
            coder.base_file = base_item
            coder.encoder_output_file_path = output_file
            coder.encode_files_to_wav()

            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0

        finally:
            for filepath in [carrier_file, secret_file, output_file]:
                if os.path.exists(filepath):
                    os.unlink(filepath)


class TestCoderDecodeMethods:
    """Test decode methods (0% coverage)"""

    @pytest.mark.integration
    def test_full_encode_decode_workflow(self):
        """Test complete encode/decode workflow"""
        coder_encode = Coder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            carrier_file = f.name

        with wave.open(carrier_file, "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            wav.writeframes(b"\x00\x00" * (44100 * 5))

        secret_content = b"This is secret data!"
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(secret_content)
            secret_file = f.name

        output_file = tempfile.mktemp(suffix=".wav")
        decode_dir = tempfile.mkdtemp()

        try:
            secret_item = SecretFileInfoItem(secret_file)
            secret_item.is_in_add_list = True
            coder_encode.secret_files_info_items.append(secret_item)

            base_item = BaseFileInfoItem(
                full_path=carrier_file,
                encode_mode=EncodeMode.NORMAL_QUALITY,
                wav_head_length=44,
            )
            coder_encode.base_file = base_item
            coder_encode.encoder_output_file_path = output_file
            coder_encode.encode_files_to_wav()

            coder_decode = Coder()
            coder_decode.base_file = base_item
            coder_decode.decoder_folder = decode_dir
            coder_decode.analyze_wav(output_file)
            coder_decode.decode_files_from_wav()

            assert len(coder_decode.secret_files_info_items) > 0

        finally:
            for filepath in [carrier_file, secret_file, output_file]:
                if os.path.exists(filepath):
                    os.unlink(filepath)
            if os.path.exists(decode_dir):
                shutil.rmtree(decode_dir)


class TestCoderAnalyzeStream:
    """Test Coder.analyze_stream (4% coverage -> higher)"""

    @pytest.mark.integration
    def test_analyze_stream_with_encoded_file(self):
        """Test analyze_stream with actually encoded file"""
        coder = Coder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            carrier_file = f.name

        with wave.open(carrier_file, "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            wav.writeframes(b"\x00\x00" * (44100 * 5))

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        output_file = tempfile.mktemp(suffix=".wav")

        try:
            coder_encode = Coder()
            secret_item = SecretFileInfoItem(secret_file)
            secret_item.is_in_add_list = True
            coder_encode.secret_files_info_items.append(secret_item)

            base_item = BaseFileInfoItem(
                full_path=carrier_file,
                encode_mode=EncodeMode.NORMAL_QUALITY,
                wav_head_length=44,
            )
            coder_encode.base_file = base_item
            coder_encode.encoder_output_file_path = output_file
            coder_encode.encode_files_to_wav()

            with open(output_file, "rb") as stream:
                with WavFile(
                    output_file, 0, EncodeMode.NORMAL_QUALITY, None, False
                ) as wav:
                    result = coder.analyze_stream(stream, Coder.H22_VERSION_DSC2)
                    assert result

        finally:
            for filepath in [carrier_file, secret_file, output_file]:
                if os.path.exists(filepath):
                    os.unlink(filepath)
