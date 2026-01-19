#!/usr/bin/env python3
import os
import shutil
import logging
import tempfile
import soundfile as sf
from pathlib import Path
from pydub import AudioSegment
from typing import Optional
from ghostbit.audiostego.core.audio_steganography import (
    Coder,
    EncodeMode,
    BaseFileInfoItem,
    SecretFileInfoItem,
    AudioSteganographyException,
)

import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub.utils")
logger = logging.getLogger("ghostbit.audiostego")


class AudioMultiFormatCoderException(Exception):
    """Base exception for steganography operations"""

    pass


class AudioMultiFormatCoder(Coder):
    """Coder class with multi-format support"""

    SUPPORTED_INPUT_FORMATS = [".wav", ".flac", ".mp3", ".m4a", ".aiff", ".aif"]
    SUPPORTED_OUTPUT_FORMATS = [".wav", ".flac", ".m4a", ".aiff", ".aif"]

    def __init__(self) -> None:
        super().__init__()
        self.temp_files: list[str] = []
        self.original_input_format: Optional[str] = None
        self.desired_output_format: str = ".wav"
        logger.debug("MultiFormatCoder initialized")

    def __del__(self) -> None:
        """Cleanup temporary files"""
        logger.debug("MultiFormatCoder destructor called, cleaning up temp files")
        self.cleanup_temp_files()

    def cleanup_temp_files(self) -> None:
        """Remove all temporary files"""
        if not self.temp_files:
            logger.debug("No temporary files to clean up")
            return

        logger.info(f"Cleaning up {len(self.temp_files)} temporary files")
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.debug(f"Deleted temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")
        self.temp_files.clear()

    def _get_file_extension(self, filepath: str) -> str:
        """Get lowercase file extension"""
        return Path(filepath).suffix.lower()

    def _convert_to_wav(self, input_file: str) -> str:
        """Convert supported audio format to WAV"""
        ext = self._get_file_extension(input_file)
        logger.debug(f"Extracted extension '{ext}' from '{input_file}'")

        if ext == ".wav":
            logger.debug(f"File already in WAV format: {input_file}")
            return input_file

        if ext not in self.SUPPORTED_INPUT_FORMATS:
            logger.error(f"Unsupported input format: {ext}")
            raise AudioMultiFormatCoderException(
                f"Unsupported input format: {ext}\n"
                f"Supported formats: {', '.join(self.SUPPORTED_INPUT_FORMATS)}"
            )

        temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_wav.close()
        temp_wav_path = temp_wav.name
        self.temp_files.append(temp_wav_path)

        logger.info(f"Converting {ext} to WAV: {input_file} -> {temp_wav_path}")
        print(f"Converting {ext} to WAV format...")

        try:
            if ext in [".flac"]:
                logger.debug("Using soundfile for FLAC conversion")
                data, samplerate = sf.read(input_file)
                logger.debug(f"Read audio: {len(data)} samples at {samplerate} Hz")
                sf.write(temp_wav_path, data, samplerate, subtype="PCM_16")
                logger.info("Conversion successful using soundfile")

            else:
                logger.debug(f"Using pydub for {ext} conversion")
                audio = AudioSegment.from_file(input_file)
                logger.debug(
                    f"Loaded audio: {len(audio)}ms, {audio.channels} channels, {audio.frame_rate} Hz"
                )
                audio.export(
                    temp_wav_path, format="wav", parameters=["-acodec", "pcm_s16le"]
                )
                logger.info("Conversion successful using Pydub")

            return temp_wav_path

        except Exception as e:
            logger.exception(f"Conversion failed for {input_file}")
            if temp_wav_path in self.temp_files:
                self.temp_files.remove(temp_wav_path)
            if os.path.exists(temp_wav_path):
                os.unlink(temp_wav_path)
            raise AudioMultiFormatCoderException(f"Conversion failed: {e}")

    def _convert_from_wav(self, wav_file: str, output_file: str) -> None:
        """Convert WAV to desired output format"""
        ext = self._get_file_extension(output_file)

        if ext == ".wav":
            if wav_file != output_file:
                logger.debug(f"Copying WAV file: {wav_file} -> {output_file}")
                shutil.copy2(wav_file, output_file)
            else:
                logger.debug("Output is same as input WAV, no copy needed")
            return

        if ext not in self.SUPPORTED_OUTPUT_FORMATS:
            logger.error(f"Unsupported output format: {ext}")
            raise AudioMultiFormatCoderException(
                f"Unsupported output format: {ext}\n"
                f"Supported formats: {', '.join(self.SUPPORTED_OUTPUT_FORMATS)}"
            )

        logger.info(f"Converting WAV to {ext.upper()}: {wav_file} -> {output_file}")
        print(f"Converting WAV to {ext.upper()} format...")

        try:
            if ext == ".flac":
                logger.debug("Using soundfile for FLAC conversion")
                data, samplerate = sf.read(wav_file)
                sf.write(output_file, data, samplerate, format="FLAC")
                logger.info("Conversion to FLAC successful using soundfile")
            else:
                logger.debug(f"Using pydub for {ext} conversion")
                audio = AudioSegment.from_wav(wav_file)
                if ext == ".flac":
                    audio.export(output_file, format="flac")
                    logger.info("Conversion to FLAC successful using pydub")
                elif ext == ".m4a":
                    audio.export(output_file, format="mp4", codec="alac")
                    logger.info("Conversion to M4A successful")
                elif ext == ".aiff":
                    audio.export(output_file, format="aiff")
                    logger.info("Conversion to AIFF successful")
                elif ext == ".aif":
                    audio.export(output_file, format="aif")
                    logger.info("Conversion to AIF successful")
                else:
                    logger.error(f"Unsupported output format: {ext}")
                    raise AudioMultiFormatCoderException(
                        f"Unsupported output format: {ext}"
                    )

            output_size = os.path.getsize(output_file)
            logger.debug(
                f"Output file size: {output_size} bytes ({output_size / 1024 / 1024:.2f} MB)"
            )

        except Exception as e:
            logger.exception(f"Output conversion failed for {output_file}")
            raise AudioMultiFormatCoderException(f"Output conversion failed: {e}")

    def encode_files_multi_format(
        self,
        carrier_file: str,
        secret_files: list[str],
        output_file: str,
        password: Optional[str] = None,
        quality_mode: EncodeMode = EncodeMode.NORMAL_QUALITY,
        use_legacy_kdf: bool = False,
    ) -> None:
        """Encode secret files into an audio file"""
        logger.info(
            f"Starting encode: carrier={carrier_file}, secrets={len(secret_files)}, output={output_file}"
        )
        logger.debug(
            f"Encode parameters: password={'set' if password else 'none'}, quality={quality_mode.name}"
        )

        self.use_legacy_kdf = use_legacy_kdf
        self.original_input_format = self._get_file_extension(carrier_file)
        self.desired_output_format = self._get_file_extension(output_file)

        dir_path = os.path.dirname(output_file)

        if dir_path:
            logger.debug(f"Creating output directory: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)

        wav_carrier = self._convert_to_wav(carrier_file)
        logger.debug("WAV file conversion step complete.")

        try:
            self.encode_quality_mode = quality_mode
            if password:
                logger.debug("Setting encryption key")
                self.encrypt = True
                if use_legacy_kdf:
                    logger.warning("Using legacy key derivation (less secure)")
                    self.set_key_unicode(password)
                else:
                    logger.info("Using secure key derivation (Argon2id)")
                    self.set_key_argon(password)

            logger.debug(f"Creating BaseFileInfoItem for {wav_carrier}")
            base_file = BaseFileInfoItem(
                full_path=wav_carrier, encode_mode=quality_mode, wav_head_length=44
            )
            self.base_file = base_file
            logger.info(
                f"Carrier capacity: {base_file.max_inner_files_size} bytes ({base_file.remains_inner_files_size_mb})"
            )
            print(f"📁 Carrier File: {os.path.basename(carrier_file)}")
            print(f"  • File Size: {base_file.file_size / 1024 / 1024:.2f} MB")
            print(f"  • File Capacity: {base_file.remains_inner_files_size_mb}")
            print(f"  • File Format: {self.original_input_format.upper()}\n")

            print(f"📁 Output File: {os.path.basename(output_file)}")
            print(f"  • Output Format: {self.desired_output_format.upper()}")
            print(f"  • Encryption: {'Yes' if password else 'No'}")
            print(f"  • Audio Quality: {quality_mode.name}")

            self.secret_files_info_items.clear()
            print("\n🔄 Adding Secret Files...")
            for secret_file in secret_files:
                if not os.path.exists(secret_file):
                    logger.warning(f"Secret file not found: {secret_file}")
                    print(f"⚠️  Warning: {secret_file} not found, skipping...")
                    continue

                info = SecretFileInfoItem(secret_file, is_in_add_list=True)
                self.secret_files_info_items.append(info)
                logger.info(
                    f"Added secret file: {info.file_name} ({info.file_size} bytes)"
                )
                print(f"  • File: {info.file_name} ({info.file_size_mb})")

            if not self.secret_files_info_items:
                logger.error("No valid secret files to encode")
                raise AudioSteganographyException("No valid secret files to encode")

            temp_encoded_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_encoded_wav.close()
            temp_encoded_wav_path = temp_encoded_wav.name
            self.temp_files.append(temp_encoded_wav_path)
            logger.debug(f"Created temporary encoded WAV: {temp_encoded_wav_path}")

            self.encoder_output_file_path = temp_encoded_wav_path

            print("\n🔄 Encoding Secret Files...")
            logger.info("Starting WAV encoding")
            self.encode_files_to_wav()
            logger.info("WAV encoding complete")

            print("\n🔄 Creating Final Output...")
            self._convert_from_wav(temp_encoded_wav_path, output_file)

            output_size = os.path.getsize(output_file)
            logger.info(f"Encoding successful: {output_file} ({output_size} bytes)")

            print(f"  • Output File: {output_file}")
            print(f"  • Output File Size: {output_size / 1024 / 1024:.2f} MB")
            print("\n✅ Encoding Complete!")
        except Exception as e:
            logger.exception("Encoding failed")
            raise AudioMultiFormatCoderException(f"Encoding failed: {e}")

        finally:
            self.cleanup_temp_files()

    def decode_files_multi_format(
        self,
        encoded_file: str,
        output_dir: str,
        password: Optional[str] = None,
        use_legacy_kdf: bool = False,
    ) -> None:
        """Decode secret files from an audio file"""
        logger.info(
            f"Starting decode: encoded_file={encoded_file}, output_dir={output_dir}"
        )
        logger.debug(f"Decode parameters: password={'set' if password else 'none'}")

        self.use_legacy_kdf = use_legacy_kdf
        self._get_file_extension(encoded_file)
        print(f"📁 Input File: '{os.path.basename(encoded_file)}'")

        wav_file = self._convert_to_wav(encoded_file)

        try:
            print("\n🔍 Analyzing file...")
            logger.info("Analyzing WAV file for hidden data")

            if password:
                logger.debug("Setting decryption key")
                if use_legacy_kdf:
                    logger.warning("Using legacy key derivation (less secure)")
                    self.set_key_unicode(password)
                else:
                    logger.info("Using secure key derivation (Argon2id)")
                    self.set_key_argon(password)

            info = self.analyze_wav(wav_file)

            if not info.h22_version:
                logger.info("No hidden data found in file")
                print("\n   😖 No hidden data found")
                print("\n✅ Decoding Complete!")
                return

            logger.info(
                f"Hidden data found: version={info.h22_version}, encrypted={self.encrypt}, files={len(self.secret_files_info_items)}"
            )

            print("\n  😎 Hidden Data Found!")
            print(f"   • Version: {info.h22_version}")
            print(f"   • Quality: {self.decode_quality_mode.name}")
            print(f"   • Encrypted: {'Yes' if self.encrypt else 'No'}")
            print(f"   • Files: {len(self.secret_files_info_items)}\n")
            print("  📄 Hidden Files:")
            for file in self.secret_files_info_items:
                logger.debug(
                    f"Found hidden file: {file.file_name} ({file.file_size} bytes)"
                )
                print(f"    • {file.file_name} ({file.file_size_mb})")

            logger.debug(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

            base_file = BaseFileInfoItem(
                full_path=wav_file,
                encode_mode=self.decode_quality_mode,
                wav_head_length=info.wav_head_length,
            )
            self.base_file = base_file
            self.decoder_folder = os.path.abspath(output_dir)
            logger.debug(f"Decoder folder set to: {self.decoder_folder}")

            print("\n🔄 Extracting Hidden Files...")
            print(f"  • Output Directory: '{output_dir}/'\n")
            logger.info("Starting file extraction")
            self.decode_files_from_wav()
            logger.info(
                f"Extraction successful: {len(self.secret_files_info_items)} files extracted"
            )
            print("✅ Decoding Complete!")

        except Exception as e:
            logger.exception("Decoding failed")
            raise AudioMultiFormatCoderException(f"Hidden file extraction failed: {e}")

        finally:
            self.cleanup_temp_files()

    def analyze_multi_format(
        self,
        audio_file: str,
        password: Optional[str] = None,
        use_legacy_kdf: bool = False,
    ) -> bool:
        """Analyze an audio file for hidden data (any supported format)"""
        logger.info(f"Analyzing file: {audio_file}")
        logger.debug(f"Analysis parameters: password={'set' if password else 'none'}")

        self.use_legacy_kdf = use_legacy_kdf
        wav_file = self._convert_to_wav(audio_file)
        logger.debug("WAV file conversion step complete.")

        print(f"📁 Input File: {os.path.basename(audio_file)}")

        try:
            if password:
                logger.debug("Setting analysis key")
                if use_legacy_kdf:
                    logger.warning("Using legacy key derivation (less secure)")
                    self.set_key_unicode(password)
                else:
                    logger.info("Using secure key derivation (Argon2id)")
                    self.set_key_argon(password)

            info = self.analyze_wav(wav_file)

            if info.h22_version:
                logger.info(
                    f"Analysis found hidden data: version={info.h22_version}, files={len(self.secret_files_info_items)}"
                )

                print("\n  😎 Hidden Data Found!")
                print(f"   • Version: {info.h22_version}")
                print(f"   • Quality: {self.decode_quality_mode.name}")
                print(f"   • Encrypted: {'Yes' if self.encrypt else 'No'}")
                print(f"   • Files: {len(self.secret_files_info_items)}")

                if self.secret_files_info_items:
                    print("\n  📄 Hidden files:")
                    for file in self.secret_files_info_items:
                        logger.debug(
                            f"Hidden file: {file.file_name} ({file.file_size} bytes)"
                        )
                        print(f"   • {file.file_name} ({file.file_size_mb})")
                print("\n✅ Analysis Complete!")
                return True
            else:
                logger.info("Analysis found no hidden data")
                print("\n   😖 No Hidden Data Found")
                print("\n✅ Analysis Complete!")
                return False

        except Exception as e:
            logger.exception("Analysis failed")
            raise AudioMultiFormatCoderException(f"Analysis failed: {e}")

        finally:
            self.cleanup_temp_files()
