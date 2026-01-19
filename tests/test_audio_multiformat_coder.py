#!/usr/bin/env python3
import os
import pytest
import tempfile
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch
from ghostbit.audiostego.core.audio_multiformat_coder import (
    AudioMultiFormatCoder,
    AudioMultiFormatCoderException,
)
from ghostbit.audiostego.core.audio_steganography import EncodeMode

"""
Tests for audiostego.core.audio_multiformat_coder module
"""

fixture_dir = Path(__file__).parent / "testcases"


class TestAudioMultiFormatCoderInitialization:
    """Test suite for AudioMultiFormatCoder initialization"""

    def test_initialization(self) -> None:
        """Test AudioMultiFormatCoder initializes correctly"""
        coder = AudioMultiFormatCoder()

        assert coder.temp_files == []
        assert coder.original_input_format is None
        assert coder.desired_output_format == ".wav"

    def test_supported_formats(self) -> None:
        """Test supported format lists"""
        assert ".wav" in AudioMultiFormatCoder.SUPPORTED_INPUT_FORMATS
        assert ".flac" in AudioMultiFormatCoder.SUPPORTED_INPUT_FORMATS
        assert ".mp3" in AudioMultiFormatCoder.SUPPORTED_INPUT_FORMATS
        assert ".m4a" in AudioMultiFormatCoder.SUPPORTED_INPUT_FORMATS

        assert ".wav" in AudioMultiFormatCoder.SUPPORTED_OUTPUT_FORMATS
        assert ".flac" in AudioMultiFormatCoder.SUPPORTED_OUTPUT_FORMATS
        assert ".m4a" in AudioMultiFormatCoder.SUPPORTED_OUTPUT_FORMATS

    def test_inherits_from_coder(self) -> None:
        """Test AudioMultiFormatCoder inherits from Coder"""
        from ghostbit.audiostego.core.audio_steganography import Coder

        coder = AudioMultiFormatCoder()

        assert isinstance(coder, Coder)


class TestAudioMultiFormatCoderFileExtension:
    """Test suite for file extension handling"""

    def test_get_file_extension_wav(self) -> None:
        """Test _get_file_extension with WAV file"""
        coder = AudioMultiFormatCoder()
        ext = coder._get_file_extension("test.wav")
        assert ext == ".wav"

    def test_get_file_extension_uppercase(self) -> None:
        """Test _get_file_extension converts to lowercase"""
        coder = AudioMultiFormatCoder()
        ext = coder._get_file_extension("test.WAV")
        assert ext == ".wav"

    def test_get_file_extension_mixed_case(self) -> None:
        """Test _get_file_extension with mixed case"""
        coder = AudioMultiFormatCoder()
        ext = coder._get_file_extension("test.FlAc")
        assert ext == ".flac"

    def test_get_file_extension_with_path(self) -> None:
        """Test _get_file_extension with full path"""
        coder = AudioMultiFormatCoder()
        ext = coder._get_file_extension("/path/to/file.mp3")
        assert ext == ".mp3"


class TestAudioMultiFormatCoderTempFileCleanup:
    """Test suite for temporary file cleanup"""

    def test_cleanup_temp_files_empty(self) -> None:
        """Test cleanup with no temp files"""
        coder = AudioMultiFormatCoder()
        coder.cleanup_temp_files()

        assert len(coder.temp_files) == 0

    def test_cleanup_temp_files_with_files(self) -> None:
        """Test cleanup removes temp files"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
            coder.temp_files.append(temp_path)

        assert os.path.exists(temp_path)

        coder.cleanup_temp_files()

        assert not os.path.exists(temp_path)
        assert len(coder.temp_files) == 0

    def test_cleanup_handles_nonexistent_files(self) -> None:
        """Test cleanup handles files that don't exist"""
        coder = AudioMultiFormatCoder()
        coder.temp_files.append("/nonexistent/file.wav")

        coder.cleanup_temp_files()

        assert len(coder.temp_files) == 0

    def test_destructor_calls_cleanup(self) -> None:
        """Test __del__ calls cleanup_temp_files"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        coder = AudioMultiFormatCoder()
        coder.temp_files.append(temp_path)

        assert os.path.exists(temp_path)

        del coder

        assert not os.path.exists(temp_path)


class TestAudioMultiFormatCoderConvertToWav:
    """Test suite for _convert_to_wav method"""

    def test_convert_to_wav_already_wav(self) -> None:
        """Test _convert_to_wav with WAV file returns same file"""
        coder = AudioMultiFormatCoder()
        test_file = str(fixture_dir / "test_carrier.wav")

        result = coder._convert_to_wav(test_file)

        assert result == test_file
        assert len(coder.temp_files) == 0

    def test_convert_to_wav_unsupported_format(self) -> None:
        """Test _convert_to_wav with unsupported format raises exception"""
        coder = AudioMultiFormatCoder()

        with pytest.raises(AudioMultiFormatCoderException) as exc_info:
            coder._convert_to_wav("test.xyz")

        assert "Unsupported input format" in str(exc_info.value)

    @patch("ghostbit.audiostego.core.audio_multiformat_coder.sf")
    def test_convert_to_wav_flac_with_soundfile(self, mock_sf: MagicMock) -> None:
        """Test _convert_to_wav FLAC with soundfile"""
        coder = AudioMultiFormatCoder()

        mock_audio_data = np.zeros((44100, 2))
        mock_sf.read.return_value = (mock_audio_data, 44100)

        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 40)
            input_file = f.name

        try:
            result = coder._convert_to_wav(input_file)

            assert result.endswith(".wav")
            assert result in coder.temp_files
            mock_sf.read.assert_called_once_with(input_file)
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            coder.cleanup_temp_files()

    @patch("ghostbit.audiostego.core.audio_multiformat_coder.AudioSegment")
    def test_convert_to_wav_mp3_with_pydub(self, mock_audio_segment: MagicMock) -> None:
        """Test _convert_to_wav MP3 with pydub"""
        coder = AudioMultiFormatCoder()

        mock_audio = MagicMock()
        mock_audio_segment.from_file.return_value = mock_audio

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            input_file = f.name

        try:
            result = coder._convert_to_wav(input_file)

            assert result.endswith(".wav")
            assert result in coder.temp_files
            mock_audio_segment.from_file.assert_called_once_with(input_file)
            mock_audio.export.assert_called_once()
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            coder.cleanup_temp_files()

    # def test_convert_to_wav_no_libraries(self) -> None:
    #     """Test _convert_to_wav with no conversion libraries"""
    #     coder = AudioMultiFormatCoder()

    #     with pytest.raises(AudioMultiFormatCoderException) as exc_info:
    #         coder._convert_to_wav("test.mp3")

    #     assert "Multi-format" in str(exc_info.value)


class TestAudioMultiFormatCoderConvertFromWav:
    """Test suite for _convert_from_wav method"""

    def test_convert_from_wav_to_wav(self) -> None:
        """Test _convert_from_wav WAV to WAV"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"test")
            input_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_file = f.name

        try:
            coder._convert_from_wav(input_file, output_file)

            assert os.path.exists(output_file)
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_convert_from_wav_unsupported_format(self) -> None:
        """Test _convert_from_wav with unsupported output format"""
        test_file = str(fixture_dir / "test_carrier.mp3")
        coder = AudioMultiFormatCoder()

        with pytest.raises(AudioMultiFormatCoderException) as exc_info:
            coder._convert_from_wav(test_file, "output.xyz")

        assert "Unsupported output format" in str(exc_info.value)

    def test_convert_from_wav_to_flac_soundfile(self) -> None:
        """Test _convert_from_wav WAV to FLAC with soundfile"""
        coder = AudioMultiFormatCoder()

        input_file = str(fixture_dir / "test_encoded.wav")
        output_file = tempfile.mktemp(suffix=".flac")

        try:
            assert input_file
            assert not os.path.exists(output_file)

            coder._convert_from_wav(str(input_file), output_file)

            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
            assert output_file.endswith(".flac")
            with open(output_file, "rb") as f:
                header = f.read(4)
                assert header == b"fLaC"
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_convert_from_wav_to_m4a_pydub(self) -> None:
        """Test _convert_from_wav WAV to M4A with pydub"""
        coder = AudioMultiFormatCoder()

        input_file = str(fixture_dir / "test_carrier.wav")
        output_file = tempfile.mktemp(suffix=".m4a")

        try:
            assert input_file
            assert not os.path.exists(output_file)

            coder._convert_from_wav(input_file, output_file)

            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
            assert output_file.endswith(".m4a")

            with open(output_file, "rb") as f:
                data = f.read(12)
                assert b"ftyp" in data, f"Expected ftyp in M4A header, got {data!r}"
                assert (
                    b"isom" in data or b"M4A" in data or b"mp42" in data
                ), f"Expected M4A brand, got {data!r}"

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestAudioMultiFormatCoderEncodeFilesMultiFormat:
    """Test suite for encode_files_multi_format method"""

    def test_encode_missing_carrier_file(self) -> None:
        """Test encode with missing carrier file"""
        coder = AudioMultiFormatCoder()

        with patch.object(coder, "_convert_to_wav", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError):
                coder.encode_files_multi_format(
                    carrier_file="/nonexistent/carrier.wav",
                    secret_files=[],
                    output_file="output.wav",
                )

    def test_encode_no_valid_secret_files(self) -> None:
        """Test encode with no valid secret files"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            carrier_file = f.name

        try:
            with patch.object(coder, "_convert_to_wav", return_value=carrier_file):
                with pytest.raises(AudioMultiFormatCoderException) as exc_info:
                    coder.encode_files_multi_format(
                        carrier_file=carrier_file,
                        secret_files=["/nonexistent1.txt", "/nonexistent2.txt"],
                        output_file="output.wav",
                    )

                assert "No valid secret files" in str(exc_info.value)
        finally:
            if os.path.exists(carrier_file):
                os.unlink(carrier_file)

    @patch("os.path.getsize")
    @patch.object(AudioMultiFormatCoder, "encode_files_to_wav")
    @patch.object(AudioMultiFormatCoder, "_convert_from_wav")
    @patch.object(AudioMultiFormatCoder, "_convert_to_wav")
    def test_encode_sets_encryption(
        self,
        mock_convert_to: MagicMock,
        mock_convert_from: MagicMock,
        mock_encode: MagicMock,
        mock_getsize: MagicMock,
    ) -> None:
        """Test encode sets encryption when password provided"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        mock_convert_to.return_value = carrier_file
        mock_getsize.return_value = 1024 * 1024

        try:
            coder.encode_files_multi_format(
                carrier_file=carrier_file,
                secret_files=[secret_file],
                output_file="output.wav",
                password="testpass",
            )

            assert coder.encrypt
        finally:
            os.unlink(carrier_file)
            os.unlink(secret_file)
            coder.cleanup_temp_files()

    @patch("ghostbit.audiostego.core.audio_multiformat_coder.os.path.getsize")
    @patch.object(AudioMultiFormatCoder, "encode_files_to_wav")
    @patch.object(AudioMultiFormatCoder, "_convert_from_wav")
    @patch.object(AudioMultiFormatCoder, "_convert_to_wav")
    def test_encode_sets_quality_mode(
        self,
        mock_convert_to: MagicMock,
        mock_convert_from: MagicMock,
        mock_encode: MagicMock,
        mock_getsize: MagicMock,
    ) -> None:
        """Test encode sets quality mode"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        mock_convert_to.return_value = carrier_file
        mock_getsize.return_value = 5 * 1024 * 1024

        try:
            coder_low = AudioMultiFormatCoder()
            coder_low.encode_files_multi_format(
                carrier_file=carrier_file,
                secret_files=[secret_file],
                output_file="output.wav",
                quality_mode=EncodeMode.LOW_QUALITY,
            )

            assert coder_low.base_file is not None
            capacity_low = coder_low.base_file.max_inner_files_size

            coder_high = AudioMultiFormatCoder()
            coder_high.encode_files_multi_format(
                carrier_file=carrier_file,
                secret_files=[secret_file],
                output_file="output.wav",
                quality_mode=EncodeMode.HIGH_QUALITY,
            )

            assert coder_high.base_file is not None
            capacity_high = coder_high.base_file.max_inner_files_size

            assert capacity_low > capacity_high
            assert capacity_low / capacity_high == pytest.approx(4.0, rel=0.1)

        finally:
            if os.path.exists(carrier_file):
                os.unlink(carrier_file)
            if os.path.exists(secret_file):
                os.unlink(secret_file)
            coder.cleanup_temp_files()


class TestAudioMultiFormatCoderDecodeFilesMultiFormat:
    """Test suite for decode_files_multi_format method"""

    def test_decode_missing_input_file(self) -> None:
        """Test decode with missing input file"""
        coder = AudioMultiFormatCoder()

        with patch.object(coder, "_convert_to_wav", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError):
                coder.decode_files_multi_format(
                    encoded_file="/nonexistent/file.wav", output_dir="/tmp/output"
                )

    @patch.object(AudioMultiFormatCoder, "analyze_wav")
    @patch.object(AudioMultiFormatCoder, "_convert_to_wav")
    def test_decode_no_hidden_data(
        self, mock_convert_to: MagicMock, mock_analyze: MagicMock
    ) -> None:
        """Test decode when no hidden data found"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        mock_convert_to.return_value = input_file

        from ghostbit.audiostego.core.audio_steganography import CarrierFileInfo

        info = CarrierFileInfo()
        info.h22_version = ""
        mock_analyze.return_value = info

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                coder.decode_files_multi_format(
                    encoded_file=input_file, output_dir=output_dir
                )

        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            coder.cleanup_temp_files()

    @patch.object(AudioMultiFormatCoder, "decode_files_from_wav")
    @patch.object(AudioMultiFormatCoder, "analyze_wav")
    @patch.object(AudioMultiFormatCoder, "_convert_to_wav")
    def test_decode_with_password(
        self,
        mock_convert_to: MagicMock,
        mock_analyze: MagicMock,
        mock_decode: MagicMock,
    ) -> None:
        """Test decode with password"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        mock_convert_to.return_value = input_file

        from ghostbit.audiostego.core.audio_steganography import CarrierFileInfo

        info = CarrierFileInfo()
        info.h22_version = "DSC2"
        info.wav_head_length = 44
        mock_analyze.return_value = info

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                coder.decode_files_multi_format(
                    encoded_file=input_file, output_dir=output_dir, password="testpass"
                )

                assert coder.aes_key is not None
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            coder.cleanup_temp_files()


class TestAudioMultiFormatCoderAnalyzeMultiFormat:
    """Test suite for analyze_multi_format method"""

    @patch.object(AudioMultiFormatCoder, "analyze_wav")
    @patch.object(AudioMultiFormatCoder, "_convert_to_wav")
    def test_analyze_returns_true_when_data_found(
        self, mock_convert_to: MagicMock, mock_analyze: MagicMock
    ) -> None:
        """Test analyze returns True when hidden data found"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        mock_convert_to.return_value = input_file

        from ghostbit.audiostego.core.audio_steganography import CarrierFileInfo

        info = CarrierFileInfo()
        info.h22_version = "DSC2"
        mock_analyze.return_value = info

        try:
            result = coder.analyze_multi_format(input_file)

            assert result
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            coder.cleanup_temp_files()

    @patch.object(AudioMultiFormatCoder, "analyze_wav")
    @patch.object(AudioMultiFormatCoder, "_convert_to_wav")
    def test_analyze_returns_false_when_no_data(
        self, mock_convert_to: MagicMock, mock_analyze: MagicMock
    ) -> None:
        """Test analyze returns False when no hidden data"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        mock_convert_to.return_value = input_file

        from ghostbit.audiostego.core.audio_steganography import CarrierFileInfo

        info = CarrierFileInfo()
        info.h22_version = ""
        mock_analyze.return_value = info

        try:
            result = coder.analyze_multi_format(input_file)

            assert not result
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            coder.cleanup_temp_files()

    @patch.object(AudioMultiFormatCoder, "analyze_wav")
    @patch.object(AudioMultiFormatCoder, "_convert_to_wav")
    def test_analyze_with_password(
        self, mock_convert_to: MagicMock, mock_analyze: MagicMock
    ) -> None:
        """Test analyze with password"""
        coder = AudioMultiFormatCoder()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        mock_convert_to.return_value = input_file

        from ghostbit.audiostego.core.audio_steganography import CarrierFileInfo

        info = CarrierFileInfo()
        info.h22_version = "DSC2"
        mock_analyze.return_value = info

        try:
            coder.analyze_multi_format(input_file, password="testpass")

            assert coder.aes_key is not None
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            coder.cleanup_temp_files()


@pytest.mark.integration
class TestAudioMultiFormatCoderIntegration:
    """Integration tests for AudioMultiFormatCoder"""

    def test_temp_files_cleaned_after_operation(self) -> None:
        """Test temp files are cleaned up after operations"""
        coder = AudioMultiFormatCoder()

        temp1 = tempfile.mktemp(suffix=".wav")
        temp2 = tempfile.mktemp(suffix=".wav")

        with open(temp1, "w") as f:
            f.write("test1")
        with open(temp2, "w") as f:
            f.write("test2")

        coder.temp_files.append(temp1)
        coder.temp_files.append(temp2)

        assert os.path.exists(temp1)
        assert os.path.exists(temp2)

        coder.cleanup_temp_files()

        assert not os.path.exists(temp1)
        assert not os.path.exists(temp2)
        assert len(coder.temp_files) == 0
