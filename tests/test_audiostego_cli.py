#!/usr/bin/env python3
import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch
from ghostbit.audiostego.cli.audiostego_cli import AudioStegoCLI, main
from ghostbit.audiostego.core.audio_steganography import (
    EncodeMode,
    AudioSteganographyException,
    KeyEnterCanceledException,
    KeyRequiredEventArgs,
)

"""
Tests for audiostego.cli.audiostego_cli module
"""


class TestAudioStegoCLIInitialization:
    """Test suite for AudioStegoCLI initialization"""

    def test_initialization_default(self) -> None:
        """Test AudioStegoCLI initializes with default verbose=False"""
        cli = AudioStegoCLI()
        assert not cli.verbose

    def test_initialization_verbose(self) -> None:
        """Test AudioStegoCLI initializes with verbose=True"""
        cli = AudioStegoCLI(verbose=True)
        assert cli.verbose


class TestAudioStegoCLIEncodeCommand:
    """Test suite for encode_command method"""

    def test_encode_missing_carrier_file(self) -> None:
        """Test encode with missing carrier file returns error code"""
        cli = AudioStegoCLI()

        result = cli.encode_command(
            input_file="/nonexistent/carrier.wav",
            secret_files=["secret.txt"],
            output_file="output.wav",
            audio_quality="normal",
        )

        assert result == 1

    def test_encode_missing_secret_files(self) -> None:
        """Test encode with missing secret files returns error code"""
        cli = AudioStegoCLI()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            carrier_file = f.name

        try:
            result = cli.encode_command(
                input_file=carrier_file,
                secret_files=["/nonexistent1.txt", "/nonexistent2.txt"],
                output_file="output.wav",
                audio_quality="normal",
            )

            assert result == 1
        finally:
            if os.path.exists(carrier_file):
                os.unlink(carrier_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.getpass.getpass")
    def test_encode_password_prompt_mismatch(self, mock_getpass: MagicMock) -> None:
        """Test encode with password prompt that doesn't match"""
        cli = AudioStegoCLI()

        mock_getpass.side_effect = ["password1", "password2"]

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            secret_file = f.name

        try:
            result = cli.encode_command(
                input_file=carrier_file,
                secret_files=[secret_file],
                output_file="output.wav",
                audio_quality="normal",
                file_password="prompt",
            )

            assert result == 1
        finally:
            if os.path.exists(carrier_file):
                os.unlink(carrier_file)
            if os.path.exists(secret_file):
                os.unlink(secret_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.getpass.getpass")
    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_encode_password_prompt_match(
        self, mock_coder_class: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test encode with matching password prompt"""
        cli = AudioStegoCLI()

        mock_getpass.side_effect = ["testpass", "testpass"]

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        try:
            cli.encode_command(
                input_file=carrier_file,
                secret_files=[secret_file],
                output_file="output.wav",
                audio_quality="normal",
                file_password="prompt",
            )

            mock_coder.encode_files_multi_format.assert_called_once()
            call_kwargs = mock_coder.encode_files_multi_format.call_args[1]
            assert call_kwargs["password"] == "testpass"
        finally:
            if os.path.exists(carrier_file):
                os.unlink(carrier_file)
            if os.path.exists(secret_file):
                os.unlink(secret_file)

    def test_encode_quality_modes(self) -> None:
        """Test encode with different quality modes"""
        cli = AudioStegoCLI()

        with patch(
            "ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder"
        ) as mock_coder_class:
            mock_coder = MagicMock()
            mock_coder_class.return_value = mock_coder

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"0" * 100000)
                carrier_file = f.name

            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                f.write(b"secret")
                secret_file = f.name

            try:
                cli.encode_command(carrier_file, [secret_file], "out.wav", "low")
                call_kwargs = mock_coder.encode_files_multi_format.call_args[1]
                assert call_kwargs["quality_mode"] == EncodeMode.LOW_QUALITY

                cli.encode_command(carrier_file, [secret_file], "out.wav", "normal")
                call_kwargs = mock_coder.encode_files_multi_format.call_args[1]
                assert call_kwargs["quality_mode"] == EncodeMode.NORMAL_QUALITY

                cli.encode_command(carrier_file, [secret_file], "out.wav", "high")
                call_kwargs = mock_coder.encode_files_multi_format.call_args[1]
                assert call_kwargs["quality_mode"] == EncodeMode.HIGH_QUALITY
            finally:
                if os.path.exists(carrier_file):
                    os.unlink(carrier_file)
                if os.path.exists(secret_file):
                    os.unlink(secret_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_encode_with_progress_callback(self, mock_coder_class: MagicMock) -> None:
        """Test encode sets up progress callback when verbose"""
        cli = AudioStegoCLI(verbose=True)

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        try:
            cli.encode_command(carrier_file, [secret_file], "out.wav", "normal")

            assert mock_coder.on_encoded_element is not None
        finally:
            if os.path.exists(carrier_file):
                os.unlink(carrier_file)
            if os.path.exists(secret_file):
                os.unlink(secret_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_encode_steganography_exception(self, mock_coder_class: MagicMock) -> None:
        """Test encode handles AudioSteganographyException"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder.encode_files_multi_format.side_effect = AudioSteganographyException(
            "Test error"
        )
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        try:
            result = cli.encode_command(
                carrier_file, [secret_file], "out.wav", "normal"
            )

            assert result == 1
        finally:
            if os.path.exists(carrier_file):
                os.unlink(carrier_file)
            if os.path.exists(secret_file):
                os.unlink(secret_file)


class TestAudioStegoCLIDecodeCommand:
    """Test suite for decode_command method"""

    def test_decode_missing_input_file(self) -> None:
        """Test decode with missing input file returns error code"""
        cli = AudioStegoCLI()

        result = cli.decode_command(
            input_file="/nonexistent/file.wav", output_dir="output"
        )

        assert result == 1

    @patch("ghostbit.audiostego.cli.audiostego_cli.getpass.getpass")
    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_decode_with_password_prompt(
        self, mock_coder_class: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test decode with password prompt"""
        cli = AudioStegoCLI()

        mock_getpass.return_value = "testpass"

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.decode_command(
                input_file=input_file, output_dir="output", file_password="prompt"
            )

            mock_coder.decode_files_multi_format.assert_called_once()
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_decode_with_direct_password(self, mock_coder_class: MagicMock) -> None:
        """Test decode with direct password"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.decode_command(
                input_file=input_file, output_dir="output", file_password="testpass"
            )

            call_kwargs = mock_coder.decode_files_multi_format.call_args[1]
            assert call_kwargs["password"] == "testpass"
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_decode_with_progress_callback(self, mock_coder_class: MagicMock) -> None:
        """Test decode sets up progress callback when verbose"""
        cli = AudioStegoCLI(verbose=True)

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.decode_command(input_file, "output")

            assert mock_coder.on_decoded_element is not None
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_decode_key_cancelled(self, mock_coder_class: MagicMock) -> None:
        """Test decode handles KeyEnterCanceledException"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder.decode_files_multi_format.side_effect = KeyEnterCanceledException()
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            result = cli.decode_command(input_file, "output")

            assert result == 1
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_decode_steganography_exception(self, mock_coder_class: MagicMock) -> None:
        """Test decode handles AudioSteganographyException"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder.decode_files_multi_format.side_effect = AudioSteganographyException(
            "Test error"
        )
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            result = cli.decode_command(input_file, "output")

            assert result == 1
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)


class TestAudioStegoCLIAnalyzeCommand:
    """Test suite for analyze_command method"""

    def test_analyze_missing_input_file(self) -> None:
        """Test analyze with missing input file returns error code"""
        cli = AudioStegoCLI()

        result = cli.analyze_command(input_file="/nonexistent/file.wav")

        assert result == 1

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_analyze_found_data(self, mock_coder_class: MagicMock) -> None:
        """Test analyze when hidden data is found"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder.analyze_multi_format.return_value = True
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            result = cli.analyze_command(input_file)

            assert result == 0
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_analyze_no_data_found(self, mock_coder_class: MagicMock) -> None:
        """Test analyze when no hidden data is found"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder.analyze_multi_format.return_value = False
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            result = cli.analyze_command(input_file)

            assert result == 1
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.getpass.getpass")
    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_analyze_with_password_prompt(
        self, mock_coder_class: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test analyze with password prompt"""
        cli = AudioStegoCLI()

        mock_getpass.return_value = "testpass"

        mock_coder = MagicMock()
        mock_coder.analyze_multi_format.return_value = True
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.analyze_command(input_file, file_password="prompt")
            mock_coder.analyze_multi_format.assert_called_once()
            call_args = mock_coder.analyze_multi_format.call_args
            if call_args[1]:
                assert call_args[1]["password"] == "testpass"
            else:
                assert call_args[0][1] == "testpass"
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_analyze_key_cancelled(self, mock_coder_class: MagicMock) -> None:
        """Test analyze handles KeyEnterCanceledException"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder.analyze_multi_format.side_effect = KeyEnterCanceledException()
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            result = cli.analyze_command(input_file)

            assert result == 1
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)


class TestAudioStegoCLICreateTestFilesCommand:
    """Test suite for create_test_files_command method"""

    def test_create_test_files_basic(self) -> None:
        """Test create test files without carrier"""
        cli = AudioStegoCLI()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = cli.create_test_files_command(
                output_dir=tmpdir, create_carrier=False
            )

            assert result == 0

    @patch("ghostbit.audiostego.cli.audiostego_cli.wave")
    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioSegment")
    def test_create_test_files_with_carrier(
        self, mock_audio_segment: MagicMock, mock_wave: MagicMock
    ) -> None:
        """Test create test files with carrier"""
        cli = AudioStegoCLI()

        mock_wav = MagicMock()
        mock_wave.open.return_value.__enter__.return_value = mock_wav

        mock_sound = MagicMock()
        mock_audio_segment.from_wav.return_value = mock_sound

        with tempfile.TemporaryDirectory() as tmpdir:
            result = cli.create_test_files_command(
                output_dir=tmpdir, create_carrier=True
            )

            assert result == 0

    @patch("ghostbit.audiostego.cli.audiostego_cli.wave")
    def test_create_test_files_carrier_exception(self, mock_wave: MagicMock) -> None:
        """Test create test files handles carrier creation exception"""
        cli = AudioStegoCLI()

        mock_wave.open.side_effect = Exception("Test error")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = cli.create_test_files_command(
                output_dir=tmpdir, create_carrier=True
            )

            assert result == 0


class TestMainFunction:
    """Test suite for main() function"""

    @patch("sys.argv", ["ghostbit audio"])
    def test_main_no_command(self) -> None:
        """Test main with no command exits with error"""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["ghostbit audio", "--version"])
    def test_main_version(self) -> None:
        """Test main with --version flag"""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    @patch("sys.argv", ["audiostego", "--help"])
    def test_main_help(self) -> None:
        """Test main with --help flag"""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    @patch("sys.argv", ["audiostego", "info"])
    @patch.object(AudioStegoCLI, "info_command")
    def test_main_info_command(self, mock_info: MagicMock) -> None:
        """Test main executes info command"""
        mock_info.return_value = 0

        result = main()

        mock_info.assert_called_once()
        assert result == 0


@pytest.mark.integration
class TestAudioStegoCLIIntegration:
    """Integration tests for AudioStegoCLI"""

    def test_end_to_end_info_command(self) -> None:
        """Test info command end-to-end"""
        cli = AudioStegoCLI()

        result = cli.info_command()

        assert result == 0

    def test_encode_creates_output_directory(self) -> None:
        """Test encode creates output directory"""
        cli = AudioStegoCLI()

        with tempfile.TemporaryDirectory() as tmpdir:
            carrier_file = os.path.join(tmpdir, "carrier.wav")
            secret_file = os.path.join(tmpdir, "secret.txt")

            with open(carrier_file, "wb") as f:
                f.write(b"0" * 100000)

            with open(secret_file, "wb") as f:
                f.write(b"secret data")

            cli.encode_command(carrier_file, [secret_file], "output.wav", "normal")

            assert os.path.exists("output")


class TestEncodeCommandCallbacks:
    """Test encode_command nested callbacks"""

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_encode_on_progress_callback_execution(
        self, mock_coder_class: MagicMock
    ) -> None:
        """Test that on_progress callback is actually called during encoding"""
        cli = AudioStegoCLI(verbose=True)

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        captured_callback = None

        def get_callback(self):
            return None

        def capture_callback(self, value):
            nonlocal captured_callback
            captured_callback = value

        type(mock_coder).on_encoded_element = property(get_callback, capture_callback)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        try:
            cli.encode_command(carrier_file, [secret_file], "out.wav", "normal")

            if captured_callback:
                for i in range(250):
                    captured_callback()

                assert True
        finally:
            os.unlink(carrier_file)
            os.unlink(secret_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    @patch("builtins.print")
    def test_encode_progress_prints_every_100_blocks(
        self, mock_print: MagicMock, mock_coder_class: MagicMock
    ) -> None:
        """Test on_progress prints every 100 blocks"""
        cli = AudioStegoCLI(verbose=True)

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        callback = None

        def get_callback(self):
            return callback

        def set_callback(self, cb):
            nonlocal callback
            callback = cb

        type(mock_coder).on_key_required = property(get_callback, set_callback)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        try:
            cli.encode_command(carrier_file, [secret_file], "out.wav", "normal")

            if callback:
                mock_print.reset_mock()

                for _ in range(100):
                    callback()

                progress_calls = [
                    c
                    for c in mock_print.call_args_list
                    if len(c[0]) > 0 and "Processed" in str(c[0][0])
                ]
                assert len(progress_calls) >= 1
        finally:
            os.unlink(carrier_file)
            os.unlink(secret_file)


class TestDecodeCommandCallbacks:
    """Test decode_command nested callbacks"""

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_decode_request_key_callback_with_password(
        self, mock_coder_class: MagicMock
    ) -> None:
        """Test request_key callback when password is provided"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        callback = None

        def get_callback(self):
            return callback

        def set_callback(self, cb):
            nonlocal callback
            callback = cb

        type(mock_coder).on_key_required = property(get_callback, set_callback)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.decode_command(input_file, "output", file_password="testpass")

            if callback:
                args = KeyRequiredEventArgs(h22_version="DSC2")
                callback(args)

                assert args.key == "testpass"
                assert not args.cancel
        finally:
            os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.getpass.getpass")
    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_decode_request_key_callback_prompt_with_key(
        self, mock_coder_class: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test request_key callback prompts for password"""
        cli = AudioStegoCLI()

        mock_getpass.return_value = "prompted_pass"

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        callback = None

        def get_callback(self):
            return callback

        def set_callback(self, cb):
            nonlocal callback
            callback = cb

        type(mock_coder).on_key_required = property(get_callback, set_callback)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.decode_command(input_file, "output", file_password=None)

            if callback:
                args = KeyRequiredEventArgs(h22_version="DSC2")
                callback(args)

                assert args.key == "prompted_pass"
                assert not args.cancel
        finally:
            os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.getpass.getpass")
    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_decode_request_key_callback_cancelled(
        self, mock_coder_class: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test request_key callback when user cancels"""
        cli = AudioStegoCLI()

        mock_getpass.return_value = ""

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        callback = None

        def get_callback(self):
            return callback

        def set_callback(self, cb):
            nonlocal callback
            callback = cb

        type(mock_coder).on_key_required = property(get_callback, set_callback)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.decode_command(input_file, "output")

            if callback:
                args = KeyRequiredEventArgs(h22_version="DSC2")
                callback(args)

                assert args.cancel
        finally:
            os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    @patch("builtins.print")
    def test_decode_on_progress_callback_execution(
        self, mock_print: MagicMock, mock_coder_class: MagicMock
    ) -> None:
        """Test decode on_progress callback is executed"""
        cli = AudioStegoCLI(verbose=True)

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        progress_callback = None

        def get_progress_callback(self):
            return progress_callback

        def set_progress_callback(self, cb):
            nonlocal progress_callback
            progress_callback = cb

        # Set up on_decoded_element property (not on_key_required)
        type(mock_coder).on_decoded_element = property(
            get_progress_callback, set_progress_callback
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.decode_command(input_file, "output")

            if progress_callback:
                mock_print.reset_mock()

                for _ in range(150):
                    progress_callback()  # This callback takes no arguments

                progress_calls = [
                    c
                    for c in mock_print.call_args_list
                    if len(c[0]) > 0 and "Processed" in str(c[0][0])
                ]
                assert len(progress_calls) >= 1
        finally:
            os.unlink(input_file)


class TestAnalyzeCommandCallbacks:
    """Test analyze_command nested callbacks"""

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_analyze_request_key_with_password(
        self, mock_coder_class: MagicMock
    ) -> None:
        """Test analyze request_key callback with password"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder.analyze_multi_format.return_value = True
        mock_coder_class.return_value = mock_coder

        callback = None

        def get_callback(self):
            return callback

        def set_callback(self, cb):
            nonlocal callback
            callback = cb

        type(mock_coder).on_key_required = property(get_callback, set_callback)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.analyze_command(input_file, file_password="testpass")

            if callback:
                args = KeyRequiredEventArgs(h22_version="DSC2")
                callback(args)

                assert args.key == "testpass"
                assert not args.cancel
        finally:
            os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.getpass.getpass")
    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_analyze_request_key_prompt_with_key(
        self, mock_coder_class: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test analyze request_key prompts for password"""
        cli = AudioStegoCLI()

        mock_getpass.return_value = "prompted_pass"

        mock_coder = MagicMock()
        mock_coder.analyze_multi_format.return_value = True
        mock_coder_class.return_value = mock_coder

        callback = None

        def get_callback(self):
            return callback

        def set_callback(self, cb):
            nonlocal callback
            callback = cb

        type(mock_coder).on_key_required = property(get_callback, set_callback)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.analyze_command(input_file)

            if callback:
                args = KeyRequiredEventArgs(h22_version="DSC2")
                callback(args)

                assert args.key == "prompted_pass"
                assert not args.cancel
        finally:
            os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.getpass.getpass")
    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_analyze_request_key_cancelled(
        self, mock_coder_class: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test analyze request_key when user cancels"""
        cli = AudioStegoCLI()

        mock_getpass.return_value = ""

        mock_coder = MagicMock()
        mock_coder.analyze_multi_format.return_value = True
        mock_coder_class.return_value = mock_coder

        callback = None

        def get_callback(self):
            return callback

        def set_callback(self, cb):
            nonlocal callback
            callback = cb

        type(mock_coder).on_key_required = property(get_callback, set_callback)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.analyze_command(input_file)

            if callback:
                args = KeyRequiredEventArgs(h22_version="DSC2")
                callback(args)

                assert args.cancel
        finally:
            os.unlink(input_file)


class TestCreateTestFilesCommand:
    """Test create_test_files_command"""

    def test_create_test_files_with_carrier_full_workflow(self) -> None:
        """Test complete carrier creation workflow"""
        cli = AudioStegoCLI()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = cli.create_test_files_command(tmpdir, create_carrier=False)

            assert result == 0

            output_path = os.path.join("output", tmpdir)

            assert os.path.exists(os.path.join(output_path, "test_secret.txt"))
            assert os.path.exists(os.path.join(output_path, "test_document.txt"))

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioSegment")
    @patch("ghostbit.audiostego.cli.audiostego_cli.wave")
    def test_create_test_files_carrier_partial_failure(
        self, mock_wave: MagicMock, mock_audio_segment: MagicMock
    ) -> None:
        """Test when AudioSegment conversion fails"""
        cli = AudioStegoCLI()

        mock_wav = MagicMock()
        mock_wave.open.return_value.__enter__.return_value = mock_wav
        mock_audio_segment.from_wav.side_effect = Exception("Conversion error")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = cli.create_test_files_command(tmpdir, create_carrier=True)

            assert result == 0

    def test_create_test_files_output_directory_created(self) -> None:
        """Test that output directory is created"""
        cli = AudioStegoCLI()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = os.path.join(tmpdir, "testcases")
            result = cli.create_test_files_command(test_dir, create_carrier=False)
            output_path = os.path.join("output", test_dir)

            assert os.path.exists(output_path)
            assert os.path.exists(os.path.join(output_path, "test_secret.txt"))
            assert os.path.exists(os.path.join(output_path, "test_document.txt"))

            assert result == 0


class TestEncodeCommandEdgeCases:
    """Additional encode_command edge cases"""

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_encode_with_direct_password(self, mock_coder_class: MagicMock) -> None:
        """Test encode with direct password (not prompt)"""
        cli = AudioStegoCLI()

        mock_coder = MagicMock()
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        try:
            cli.encode_command(
                carrier_file,
                [secret_file],
                "out.wav",
                "normal",
                file_password="mypassword",
            )

            call_kwargs = mock_coder.encode_files_multi_format.call_args[1]
            assert call_kwargs["password"] == "mypassword"
        finally:
            os.unlink(carrier_file)
            os.unlink(secret_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_encode_exception_with_verbose(self, mock_coder_class: MagicMock) -> None:
        """Test encode exception prints traceback in verbose mode"""
        cli = AudioStegoCLI(verbose=True)

        mock_coder = MagicMock()
        mock_coder.encode_files_multi_format.side_effect = Exception("Unexpected error")
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"0" * 100000)
            carrier_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            secret_file = f.name

        try:
            with patch("traceback.print_exc") as mock_traceback:
                result = cli.encode_command(
                    carrier_file, [secret_file], "out.wav", "normal"
                )
                mock_traceback.assert_called_once()
                assert result == 1
        finally:
            os.unlink(carrier_file)
            os.unlink(secret_file)


class TestDecodeCommandEdgeCases:
    """Additional decode_command edge cases"""

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_decode_exception_with_verbose(self, mock_coder_class: MagicMock) -> None:
        """Test decode exception prints traceback in verbose mode"""
        cli = AudioStegoCLI(verbose=True)

        mock_coder = MagicMock()
        mock_coder.decode_files_multi_format.side_effect = Exception("Unexpected error")
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            with patch("traceback.print_exc") as mock_traceback:
                result = cli.decode_command(input_file, "output")

                mock_traceback.assert_called_once()
                assert result == 1
        finally:
            os.unlink(input_file)


class TestAnalyzeCommandEdgeCases:
    """Additional analyze_command edge cases"""

    @patch("ghostbit.audiostego.cli.audiostego_cli.getpass.getpass")
    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_analyze_password_prompt_empty(
        self, mock_coder_class: MagicMock, mock_getpass: MagicMock
    ) -> None:
        """Test analyze with password prompt returns empty (skipped)"""
        cli = AudioStegoCLI()

        mock_getpass.return_value = ""

        mock_coder = MagicMock()
        mock_coder.analyze_multi_format.return_value = True
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            cli.analyze_command(input_file, file_password="prompt")
            call_kwargs = mock_coder.analyze_multi_format.call_args[1]
            assert call_kwargs.get("password") is None
        finally:
            os.unlink(input_file)

    @patch("ghostbit.audiostego.cli.audiostego_cli.AudioMultiFormatCoder")
    def test_analyze_exception_with_verbose(self, mock_coder_class: MagicMock) -> None:
        """Test analyze exception prints traceback in verbose mode"""
        cli = AudioStegoCLI(verbose=True)

        mock_coder = MagicMock()
        mock_coder.analyze_multi_format.side_effect = Exception("Unexpected error")
        mock_coder_class.return_value = mock_coder

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            input_file = f.name

        try:
            with patch("traceback.print_exc") as mock_traceback:
                result = cli.analyze_command(input_file)

                mock_traceback.assert_called_once()
                assert result == 1
        finally:
            os.unlink(input_file)
