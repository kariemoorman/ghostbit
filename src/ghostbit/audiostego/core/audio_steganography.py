#!/usr/bin/env python3
import os
import struct
import hashlib
import logging
from enum import Enum
from Crypto.Cipher import AES
from dataclasses import dataclass
from Crypto.Util.Padding import pad
from argon2.low_level import hash_secret_raw, Type as Argon2Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import List, Optional, Callable, BinaryIO, Any, Type
from types import TracebackType

logger = logging.getLogger("ghostbit.audiostego")

AESCipher = Any


class EncodeMode(Enum):
    """Quality modes for encoding data"""

    LOW_QUALITY = 2
    NORMAL_QUALITY = 4
    HIGH_QUALITY = 8


class AudioSteganographyException(Exception):
    """Base exception for audio steganography operations"""

    pass


class KeyEnterCanceledException(Exception):
    """Exception raised when key entry is cancelled"""

    pass


@dataclass
class KeyRequiredEventArgs:
    """Arguments for key required event"""

    key: str = ""
    cancel: bool = False
    h22_version: str = ""


@dataclass
class SecretFileInfoItem:
    """Information about a secret file"""

    full_path: str
    is_in_add_list: bool = False
    file_size: int = 0
    start_position: int = 0
    end_position: int = 0

    def __post_init__(self) -> None:
        self.file_name = os.path.basename(self.full_path)
        if self.is_in_add_list:
            if os.path.exists(self.full_path):
                self.file_size = os.path.getsize(self.full_path)
                logger.debug(
                    f"SecretFileInfoItem created: {self.file_name} ({self.file_size} bytes)"
                )
            else:
                logger.warning(
                    f"SecretFileInfoItem file does not exist: {self.full_path}"
                )
        else:
            logger.debug(
                f"SecretFileInfoItem for extraction: {self.file_name} ({self.file_size} bytes)"
            )

    @property
    def file_size_mb(self) -> str:
        """Get file size in MB as formatted string"""
        size_mb = self.file_size / 1024.0 / 1024.0
        if size_mb < 0.1:
            return " < 0.1 MB"
        return f"{size_mb:.1f} MB"


@dataclass
class BaseFileInfoItem:
    """Information about the carrier WAV file"""

    full_path: str
    encode_mode: EncodeMode
    wav_head_length: int
    file_size: int = 0
    inner_files_size: int = 0
    max_inner_files_size: int = 0

    def __post_init__(self) -> None:
        self.file_name = os.path.basename(self.full_path)
        if os.path.exists(self.full_path):
            self.file_size = os.path.getsize(self.full_path)
            self.max_inner_files_size = (
                self.file_size - self.wav_head_length - 104
            ) // self.encode_mode.value
            logger.debug(
                f"BaseFileInfoItem: {self.file_name}, size={self.file_size}, capacity={self.max_inner_files_size}"
            )
        else:
            logger.warning(f"BaseFileInfoItem file does not exist: {self.full_path}")

    @property
    def remains_inner_files_size(self) -> int:
        """Get remaining capacity for hidden files"""
        remains = self.max_inner_files_size - self.inner_files_size - 32 - 19
        return max(0, remains)

    @property
    def remains_inner_files_size_mb(self) -> str:
        """Get remaining capacity in MB as formatted string"""
        remains = self.remains_inner_files_size
        size_mb = remains / 1024.0 / 1024.0
        if size_mb < 0.1:
            return f"{remains} Bytes"
        return f"{size_mb:.1f} MB"

    def add_inner_file_size(self, size: int) -> bool:
        """Add a file size to the inner files. Returns False if it doesn't fit."""
        if size > self.remains_inner_files_size:
            logger.warning(
                f"Cannot add file of size {size}: exceeds remaining capacity {self.remains_inner_files_size}"
            )
            return False
        self.inner_files_size += size + 32 + 19
        logger.debug(
            f"Added file size {size}, new inner_files_size={self.inner_files_size}"
        )
        return True

    def remove_inner_file_size(self, size: int) -> None:
        """Remove a file size from the inner files"""
        self.inner_files_size -= size + 32 + 19
        logger.debug(
            f"Removed file size {size}, new inner_files_size={self.inner_files_size}"
        )


@dataclass
class CarrierFileInfo:
    """Information about the analyzed carrier file"""

    file_name: str = ""
    wav_head_length: int = 0
    h22_version: str = ""


class Chunk:
    """Represents a RIFF chunk in a WAV file"""

    PCM_AUDIO_FORMAT = 1
    RIFF_CHUNK_ID = "RIFF"
    DATA_CHUNK_ID = "DATA"
    FORMAT_CHUNK_ID = "FMT "
    WAVE_FORMAT_KEY = "WAVE"

    def __init__(self, wave_stream: BinaryIO) -> None:
        id_data = wave_stream.read(4)
        size_data = wave_stream.read(4)

        self.chunk_id = id_data.decode("ascii", errors="ignore").upper()
        self.chunk_size: int = struct.unpack("<I", size_data)[0]

        logger.debug(f"Chunk: id={self.chunk_id}, size={self.chunk_size}")

        if self.chunk_id == "DATA":
            self.all_chunk_data = id_data + size_data
            return

        if self.chunk_size <= 0:
            logger.error(f"Invalid chunk size: {self.chunk_size}")
            raise AudioSteganographyException("Invalid chunk size")

        if self.chunk_id != "RIFF":
            chunk_content = wave_stream.read(self.chunk_size)
            self.all_chunk_data = id_data + size_data + chunk_content
        else:
            self.all_chunk_data = b""

    @property
    def chunk_size_with_header(self) -> int:
        return self.chunk_size + 8


class RiffChunk(Chunk):
    """RIFF chunk specific to WAV files"""

    def __init__(self, wave_stream: BinaryIO) -> None:
        id_data = wave_stream.read(4)
        size_data = wave_stream.read(4)
        format_data = wave_stream.read(4)

        self.chunk_id = id_data.decode("ascii", errors="ignore")
        self.chunk_size = struct.unpack("<I", size_data)[0]
        self.format = format_data.decode("ascii", errors="ignore")
        self.header_data = id_data + size_data + format_data

        logger.debug(f"RiffChunk: format={self.format}, size={self.chunk_size}")


class FormatChunk(Chunk):
    """Format chunk containing audio format information"""

    def __init__(self, orig_chunk: Chunk) -> None:
        if orig_chunk.chunk_id != "FMT ":
            logger.error(f"Invalid chunk type for FormatChunk: {orig_chunk.chunk_id}")
            raise AudioSteganographyException(
                f"Invalid chunk type: {orig_chunk.chunk_id}"
            )

        self.chunk_id = orig_chunk.chunk_id
        self.chunk_size = orig_chunk.chunk_size
        self.all_chunk_data = orig_chunk.all_chunk_data

        if len(self.all_chunk_data) >= 12:
            self.audio_format = struct.unpack("<H", self.all_chunk_data[8:10])[0]
            self.number_of_channels = struct.unpack("<H", self.all_chunk_data[10:12])[0]
            logger.debug(
                f"FormatChunk: format={self.audio_format}, channels={self.number_of_channels}"
            )


class WavFile:
    """Handles reading and writing WAV files"""

    HEAD26_LENGTH = 26
    HEAD26_EXTENDED_LENGTH = 56

    def __init__(
        self,
        file_name: str,
        buff_size: int,
        encode_mode: EncodeMode,
        key_verif_block: Optional[bytes],
        read_head22: bool,
        kdf_version: int = 0,
        salt: Optional[bytes] = None,
    ) -> None:
        logger.info(f"Opening WAV file: {file_name}")
        logger.debug(
            f"WavFile params: buff_size={buff_size}, mode={encode_mode.name}, read_head22={read_head22}"
        )

        self.file_name = file_name
        self.buff_size = buff_size
        self.encode_mode = encode_mode
        self.file_stream = open(file_name, "rb")
        self.current_block = bytearray()
        self.size_last_block = 0
        self.is_last_block = False
        self.head = bytearray()
        self.head26 = bytearray()
        self.head26_block = bytearray()
        self.kdf_version = kdf_version
        self.salt = salt

        try:
            self.riff = RiffChunk(self.file_stream)
            if self.riff.chunk_id != "RIFF" or self.riff.format.upper() != "WAVE":
                logger.error(
                    f"Invalid WAV format: id={self.riff.chunk_id}, format={self.riff.format}"
                )
                raise AudioSteganographyException("Invalid WAV file format")

            self.head.extend(self.riff.header_data)
            self.format_chunk = None

            while True:
                chunk = Chunk(self.file_stream)
                if chunk.all_chunk_data:
                    self.head.extend(chunk.all_chunk_data)

                if chunk.chunk_id == "FMT ":
                    self.format_chunk = FormatChunk(chunk)

                if chunk.chunk_id == "DATA":
                    logger.debug("Found DATA chunk, WAV header complete")
                    break

            if not self.format_chunk:
                logger.error("Format chunk not found in WAV file")
                raise AudioSteganographyException("Format chunk not found")

            if self.format_chunk.audio_format != Chunk.PCM_AUDIO_FORMAT:
                logger.error(
                    f"Unsupported audio format: {self.format_chunk.audio_format}"
                )
                raise AudioSteganographyException("Only PCM audio format is supported")

            if read_head22:
                if key_verif_block:
                    if self.kdf_version == 1:
                        self.head26 = bytearray(self.HEAD26_EXTENDED_LENGTH)
                        self.head26_block = bytearray(self.file_stream.read(224))
                        self.head26[0:4] = b"DSC2"
                        self.head26[4] = encode_mode.value
                        self.head26[5] = 1
                        self.head26[6] = kdf_version
                        self.head26[7:23] = salt if salt else b"\x00" * 16
                        self.head26[23:56] = key_verif_block
                        logger.debug(
                            "Created extended head26 with Argon2id info (43 bytes)"
                        )
                    else:
                        self.head26 = bytearray(26)
                        self.head26_block = bytearray(self.file_stream.read(104))
                        self.head26[0:4] = b"DSC2"
                        self.head26[4] = encode_mode.value
                        self.head26[5] = 1
                        self.head26[6:26] = key_verif_block
                        logger.debug("Created legacy head26 with encryption (26 bytes)")
                else:
                    self.head26 = bytearray(6)
                    self.head26_block = bytearray(self.file_stream.read(24))
                    self.head26[0:4] = b"DSC2"
                    self.head26[4] = encode_mode.value
                    self.head26[5] = 0
                    logger.debug("Read head26 without encryption")

        except Exception as e:
            logger.exception(f"Error reading WAV file {file_name}")
            self.file_stream.close()
            raise AudioSteganographyException(f"Error reading WAV file: {e}")

    def read_block(self) -> None:
        """Read the next block of data"""
        if self.is_last_block:
            return

        current_pos = self.file_stream.tell()
        self.file_stream.seek(0, 2)
        file_length = self.file_stream.tell()
        self.file_stream.seek(current_pos)

        remaining = file_length - current_pos

        if remaining <= self.buff_size:
            self.size_last_block = remaining
            self.current_block = bytearray(self.file_stream.read(remaining))
            self.is_last_block = True
            logger.debug(f"Read last block: {self.size_last_block} bytes")
        else:
            self.current_block = bytearray(self.file_stream.read(self.buff_size))
            logger.debug(f"Read block: {len(self.current_block)} bytes")

    def read_rest_data(self) -> None:
        """Read remaining data from current position to end"""
        current_pos = self.file_stream.tell()
        self.file_stream.seek(0, 2)
        file_length = self.file_stream.tell()
        self.file_stream.seek(current_pos)

        self.size_last_block = file_length - current_pos
        self.current_block = bytearray(self.file_stream.read(self.size_last_block))
        logger.debug(f"Read rest of data: {self.size_last_block} bytes")

    def seek_in_stream(self, offset: int) -> None:
        """Seek relative to current position"""
        self.file_stream.seek(offset, 1)
        logger.debug(f"Seek relative: {offset} bytes")

    def seek_from_begin(self, offset: int) -> None:
        """Seek from beginning of file"""
        self.file_stream.seek(offset, 0)
        logger.debug(f"Seek from beginning: {offset} bytes")

    def close(self) -> None:
        """Close the file stream"""
        if self.file_stream:
            self.file_stream.close()
            logger.debug(f"Closed WAV file: {self.file_name}")

    def __enter__(self) -> "WavFile":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()


class SecretFile:
    """Handles reading secret files to be hidden"""

    SECRET_HEAD_SIZE = 32
    SECRET_END_HEAD_SIZE = 4
    SECRET_END_HEAD_SIZE_MAX = 19

    def __init__(
        self,
        file_name: str,
        buff_size: int,
        mode: EncodeMode,
        aes_cipher: Optional[AESCipher] = None,
    ) -> None:
        logger.info(f"Opening secret file: {file_name}")
        logger.debug(
            f"SecretFile params: buff_size={buff_size}, mode={mode.name}, encrypted={aes_cipher is not None}"
        )

        self.file_name = file_name
        self.buff_size = buff_size // mode.value
        self.mode = mode
        self.aes_cipher = aes_cipher
        self.file_stream = open(file_name, "rb")
        self.current_block = bytearray(self.buff_size)
        self.size_last_block = 0
        self.is_last_block = False
        self.file_stream.seek(0, 2)
        file_length = self.file_stream.tell()
        self.file_stream.seek(0, 0)

        logger.debug(f"Secret file size: {file_length} bytes")

        name = os.path.basename(file_name)
        ext = os.path.splitext(name)[1][:5]
        base_name = os.path.splitext(name)[0][:25]
        full_name = base_name + ext

        header = b"DSSF" + full_name.encode("ascii", errors="replace").ljust(
            20, b"\x00"
        )
        self.current_block[0 : len(header)] = header

        self.current_block[24:28] = struct.pack(">I", file_length)

        if file_length + 32 <= self.buff_size:
            self.size_last_block = file_length + 32
            data = self.file_stream.read(file_length)
            self.current_block[32 : 32 + len(data)] = data
            self.is_last_block = True
            self._handle_last_block()
            logger.debug("Secret file fits in single block")
        else:
            data = self.file_stream.read(self.buff_size - 32)
            self.current_block[32 : 32 + len(data)] = data
            logger.debug("Secret file requires multiple blocks")

    def read_block(self) -> None:
        """Read the next block"""
        if self.is_last_block:
            return

        current_pos = self.file_stream.tell()
        self.file_stream.seek(0, 2)
        file_length = self.file_stream.tell()
        self.file_stream.seek(current_pos)

        remaining = file_length - current_pos

        if remaining <= self.buff_size:
            self.size_last_block = remaining
            self.current_block = bytearray(self.file_stream.read(remaining))
            self.is_last_block = True
            self._handle_last_block()
            logger.debug(
                f"Read last block of secret file: {self.size_last_block} bytes"
            )
        else:
            self.current_block = bytearray(self.file_stream.read(self.buff_size))
            logger.debug(f"Read block of secret file: {len(self.current_block)} bytes")

    def _handle_last_block(self) -> None:
        """Handle the last block by adding padding and end marker"""
        padding_size = 16 - (self.size_last_block + 4) % 16
        self.current_block = bytearray(self.current_block[: self.size_last_block])
        self.current_block.extend(b"\x00" * padding_size)
        self.current_block.extend(b"DSSF")
        self.size_last_block += 4 + padding_size
        logger.debug(
            f"Added padding ({padding_size} bytes) and end marker to last block"
        )

    def get_current_block(self) -> bytes:
        """Get current block, encrypted if cipher is set"""
        if self.aes_cipher:
            block = bytes(self.current_block)
            logger.debug(f"Encrypted block: {len(block)} bytes")
            return bytes(self.aes_cipher.encrypt(block))
        return bytes(self.current_block)

    def close(self) -> None:
        """Close the file stream"""
        if self.file_stream:
            self.file_stream.close()
            logger.debug(f"Closed secret file: {self.file_name}")

    def __enter__(self) -> "SecretFile":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()


class DecodedFile:
    """Handles reading and decoding hidden files"""

    def __init__(
        self,
        stream: BinaryIO,
        buff_size: int,
        start_pos: int,
        end_pos: int,
        mode: EncodeMode,
    ):
        logger.debug(f"DecodedFile: start={start_pos}, end={end_pos}, mode={mode.name}")

        self.stream = stream
        self.buff_size = buff_size
        self.start_position = start_pos
        self.end_position = end_pos
        self.mode = mode
        self.count_buffers = (end_pos - start_pos) // buff_size
        self.num_of_buff = 0
        self.current_block = bytearray()
        self.size_current_block = buff_size
        self.is_last_block = False
        self.padd_length = 0

        stream.seek(start_pos, 0)

    def read_block(self) -> None:
        """Read the next block"""
        if self.is_last_block:
            return

        if self.num_of_buff == self.count_buffers:
            self.is_last_block = True
            current_pos = self.stream.tell()
            self.size_current_block = self.end_position - current_pos
            self.padd_length = (
                16 - (self.size_current_block // self.mode.value + 4) % 16
            )
            self.size_current_block += (self.padd_length + 4) * self.mode.value
            self.current_block = bytearray(self.stream.read(self.size_current_block))
            logger.debug(
                f"Read last decoded block: {self.size_current_block} bytes, padding={self.padd_length}"
            )
        else:
            self.current_block = bytearray(self.stream.read(self.buff_size))
            self.num_of_buff += 1
            logger.debug(
                f"Read decoded block {self.num_of_buff}: {len(self.current_block)} bytes"
            )


class Coder:
    """Main class for encoding and decoding steganography operations"""

    H22_VERSION_DSCF = "DSCF"
    H22_VERSION_DSC2 = "DSC2"
    H32_VERSION_DSSF = "DSSF"
    AES_BLOCK_SIZE = 16
    AES_KEY_SIZE = 32
    KEY_VERIF_BLOCK_SIZE = 20
    CD_HEAD26_TRY_FIND_LIMIT = 882000
    OTHER_HEAD26_TRY_FIND_LIMIT = 352800
    KDF_VERSION_LEGACY = 0
    KDF_VERSION_ARGON2ID = 1

    def __init__(self) -> None:
        logger.debug("Coder initialized")

        self.base_file_info = CarrierFileInfo()
        self.original_base_file = ""
        self.base_file: Optional[BaseFileInfoItem] = None
        self.buff_size = 1048576
        self.key_verif_block = bytearray()
        self.aes_key = bytearray(self.AES_KEY_SIZE)
        self.encrypt = False
        self.encode_quality_mode = EncodeMode.NORMAL_QUALITY
        self.decode_quality_mode = EncodeMode.NORMAL_QUALITY
        self.encoder_output_file_path = ""
        self.decoder_folder = ""
        self.secret_files_info_items: List[SecretFileInfoItem] = []
        self.on_encoded_element: Optional[Callable[[], None]] = None
        self.on_decoded_element: Optional[Callable[[], None]] = None
        self.on_key_required: Optional[Callable[[KeyRequiredEventArgs], None]] = None
        self.use_legacy_kdf = False
        self.kdf_version: int = self.KDF_VERSION_ARGON2ID
        self.salt: Optional[bytes] = None

    def set_buff_size(self, size: int) -> None:
        """Set buffer size with validation"""
        if size > 536870912 or size < 1024 or size % 16 != 0:
            logger.warning(f"Invalid buffer size {size}, using default 1MB")
            self.buff_size = 1048576
        else:
            logger.debug(f"Buffer size set to {size}")
            self.buff_size = size

    def set_key_ascii(self, key: str) -> None:
        """Set encryption key (ASCII mode)"""
        logger.info("Setting ASCII encryption key")
        key_bytes = key.encode("ascii", errors="replace")[: self.AES_KEY_SIZE]
        self.aes_key = bytearray(key_bytes.ljust(self.AES_KEY_SIZE, b"\x00"))
        self.key_verif_block = bytearray(hashlib.sha1(bytes(self.aes_key)).digest())
        logger.debug("ASCII key and verification block set")

    def set_key_unicode(self, key: str) -> None:
        """Set encryption key (Unicode mode)"""
        logger.info("Setting Unicode encryption key")
        key_bytes = key.encode("utf-16-le")
        hash_bytes = hashlib.sha256(key_bytes).digest()
        self.aes_key = bytearray(hash_bytes)
        self.kdf_version = self.KDF_VERSION_LEGACY
        self.salt = None
        cipher = AES.new(bytes(self.aes_key), AES.MODE_CBC, bytes(self.aes_key[:16]))
        padded_key = pad(bytes(self.aes_key), AES.block_size)
        encrypted = cipher.encrypt(padded_key)
        self.key_verif_block = bytearray(hashlib.sha1(encrypted).digest())
        logger.debug("Unicode key and verification block set")
        logger.debug(f"Unicode key set (kdf_version={self.kdf_version})")

    def set_key_argon(self, password: str) -> None:
        """Secure key derivation with Argon2id and proper verification"""

        self.kdf_version = self.KDF_VERSION_ARGON2ID
        if not self.salt:
            self.salt = os.urandom(16)

        self.aes_key = bytearray(
            hash_secret_raw(
                secret=password.encode("utf-8"),
                salt=self.salt,
                time_cost=3,
                memory_cost=65536,
                parallelism=4,
                hash_len=32,
                type=Argon2Type.ID,
            )
        )

        verification_plaintext = b"STEGO_VERIFY_2025"
        nonce = self.salt[:12]

        aesgcm = AESGCM(bytes(self.aes_key))
        verification_ciphertext = aesgcm.encrypt(nonce, verification_plaintext, None)

        self.key_verif_block = bytearray(verification_ciphertext)

        logger.debug(f"Secure Argon2id key set (kdf_version={self.kdf_version})")

    def _get_cipher(self) -> AESCipher:
        """Get AES cipher for encryption/decryption"""
        logger.debug("Creating AES cipher")
        return AES.new(bytes(self.aes_key), AES.MODE_ECB)

    def encode_data(
        self, base_data: bytearray, secret_data: bytes, length: int
    ) -> bytearray:
        """Encode secret data into base data using LSB steganography"""
        logger.debug(
            f"Encoding {length} bytes with {self.encode_quality_mode.name} quality"
        )
        result = bytearray(base_data)

        if self.encode_quality_mode == EncodeMode.LOW_QUALITY:
            for i in range(length):
                result[i * 2] = secret_data[i]

        elif self.encode_quality_mode == EncodeMode.NORMAL_QUALITY:
            for i in range(length):
                idx = i * 4
                result[idx] = (result[idx] & 0xF0) | ((secret_data[i] & 0xF0) >> 4)
                result[idx + 2] = (result[idx + 2] & 0xF0) | (secret_data[i] & 0x0F)

        elif self.encode_quality_mode == EncodeMode.HIGH_QUALITY:
            for i in range(length):
                idx = i * 8
                result[idx] = (result[idx] & 0xFC) | ((secret_data[i] & 0xC0) >> 6)
                result[idx + 2] = (result[idx + 2] & 0xFC) | (
                    (secret_data[i] & 0x30) >> 4
                )
                result[idx + 4] = (result[idx + 4] & 0xFC) | (
                    (secret_data[i] & 0x0C) >> 2
                )
                result[idx + 6] = (result[idx + 6] & 0xFC) | (secret_data[i] & 0x03)

        return result

    def decode_data(self, base_data: bytes, length: int) -> bytearray:
        """Decode secret data from base data"""
        result_size = length // self.decode_quality_mode.value
        logger.debug(
            f"Decoding {length} bytes with {self.decode_quality_mode.name} quality -> {result_size} bytes"
        )
        result = bytearray(result_size)

        if self.decode_quality_mode == EncodeMode.LOW_QUALITY:
            for i in range(result_size):
                result[i] = base_data[i * 2]

        elif self.decode_quality_mode == EncodeMode.NORMAL_QUALITY:
            for i in range(result_size):
                idx = i * 4
                result[i] = ((base_data[idx] & 0x0F) << 4) | (base_data[idx + 2] & 0x0F)

        elif self.decode_quality_mode == EncodeMode.HIGH_QUALITY:
            for i in range(result_size):
                idx = i * 8
                result[i] = (
                    ((base_data[idx] & 0x03) << 6)
                    | ((base_data[idx + 2] & 0x03) << 4)
                    | ((base_data[idx + 4] & 0x03) << 2)
                    | (base_data[idx + 6] & 0x03)
                )
        return result

    def encode_files_to_wav(self) -> None:
        """Encode secret files into a WAV file"""
        if self.base_file is None:
            logger.error("Base file not set")
            raise AudioSteganographyException(
                "Base file not set. Initialize with set_base_file() first."
            )

        logger.info(f"Starting WAV encoding to {self.encoder_output_file_path}")
        logger.debug(
            f"Encoding {len(self.secret_files_info_items)} files with {self.encode_quality_mode.name} quality"
        )

        with open(self.encoder_output_file_path, "wb") as out_stream:
            cipher = self._get_cipher() if self.encrypt else None
            key_block = bytes(self.key_verif_block) if self.encrypt else None

            with WavFile(
                self.base_file.full_path,
                self.buff_size,
                self.encode_quality_mode,
                key_block,
                True,
                kdf_version=self.kdf_version,
                salt=self.salt,
            ) as wav_file:

                out_stream.write(bytes(wav_file.head))
                logger.debug(f"Wrote WAV header: {len(wav_file.head)} bytes")

                original_mode = self.encode_quality_mode
                self.encode_quality_mode = EncodeMode.NORMAL_QUALITY

                head26_size = len(wav_file.head26)
                head26_block_size = len(wav_file.head26_block)
                required_block_size = head26_size * self.encode_quality_mode.value

                if head26_block_size < required_block_size:
                    logger.error(
                        f"Buffer size mismatch: head26={head26_size}, block={head26_block_size}, required={required_block_size}"
                    )
                    raise AudioSteganographyException(
                        f"head26_block too small: got {head26_block_size}, need {required_block_size}"
                    )

                logger.debug(
                    f"Encoding head26: {head26_size} bytes into {head26_block_size} byte block"
                )

                encoded_head26 = self.encode_data(
                    wav_file.head26_block, bytes(wav_file.head26), len(wav_file.head26)
                )
                out_stream.write(bytes(encoded_head26))
                logger.debug("Wrote encoded head26")

                self.encode_quality_mode = original_mode

                for idx, secret_file_info in enumerate(self.secret_files_info_items):
                    if not secret_file_info.is_in_add_list:
                        continue

                    logger.info(
                        f"Encoding file {idx}/{len(self.secret_files_info_items)}: {secret_file_info.file_name}"
                    )

                    with SecretFile(
                        secret_file_info.full_path,
                        self.buff_size,
                        self.encode_quality_mode,
                        cipher,
                    ) as secret_file:

                        wav_file.read_block()

                        while not secret_file.is_last_block:
                            secret_block = secret_file.get_current_block()
                            encoded = self.encode_data(
                                wav_file.current_block, secret_block, len(secret_block)
                            )
                            out_stream.write(bytes(encoded))

                            secret_file.read_block()
                            wav_file.read_block()

                            if self.on_encoded_element:
                                self.on_encoded_element()

                        secret_block = secret_file.get_current_block()
                        encoded = self.encode_data(
                            wav_file.current_block,
                            secret_block[: secret_file.size_last_block],
                            secret_file.size_last_block,
                        )
                        write_size = (
                            secret_file.size_last_block * self.encode_quality_mode.value
                        )
                        out_stream.write(bytes(encoded[:write_size]))

                        if wav_file.is_last_block:
                            seek_back = -(wav_file.size_last_block - write_size)
                            wav_file.seek_in_stream(seek_back)
                            wav_file.read_rest_data()
                        else:
                            seek_back = -(len(wav_file.current_block) - write_size)
                            wav_file.seek_in_stream(seek_back)

                        if self.on_encoded_element:
                            self.on_encoded_element()

                    logger.debug(f"Completed encoding {secret_file_info.file_name}")

                wav_file.read_block()
                while not wav_file.is_last_block:
                    out_stream.write(bytes(wav_file.current_block))
                    wav_file.read_block()

                out_stream.write(
                    bytes(wav_file.current_block[: wav_file.size_last_block])
                )

        output_size = os.path.getsize(self.encoder_output_file_path)
        logger.info(f"WAV encoding complete: {output_size} bytes written")

    def decode_files_from_stream(self, stream: BinaryIO) -> None:
        """Decode secret files from a stream"""
        logger.info(
            f"Starting stream decoding: {len(self.secret_files_info_items)} files"
        )
        cipher = self._get_cipher() if self.encrypt else None

        for idx, secret_file_info in enumerate(self.secret_files_info_items):
            if secret_file_info.is_in_add_list:
                continue

            logger.info(
                f"Decoding file {idx}/{len(self.secret_files_info_items)}: {secret_file_info.file_name}"
            )

            decoded_file = DecodedFile(
                stream,
                self.buff_size,
                secret_file_info.start_position,
                secret_file_info.end_position,
                self.decode_quality_mode,
            )

            output_path = os.path.join(self.decoder_folder, secret_file_info.full_path)
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                logger.debug(f"Created output directory: {output_dir}")

            with open(output_path, "wb") as out_file:
                while not decoded_file.is_last_block:
                    decoded_file.read_block()
                    decoded_data = self.decode_data(
                        bytes(decoded_file.current_block),
                        decoded_file.size_current_block,
                    )

                    if self.encrypt and cipher:
                        decoded_data = bytearray(cipher.decrypt(bytes(decoded_data)))

                    if decoded_file.is_last_block:
                        trim_size = len(decoded_data) - decoded_file.padd_length - 4
                        decoded_data = decoded_data[:trim_size]

                    out_file.write(bytes(decoded_data))

                    if self.on_decoded_element:
                        self.on_decoded_element()

                bytes_written = len(bytes(decoded_data))
                logger.info(
                    f"Decoded {secret_file_info.file_name}: {bytes_written} bytes written to {output_path}"
                )

    def decode_files_from_wav(self) -> None:
        """Decode secret files from a WAV file"""
        if self.base_file is None:
            logger.error("Base file not set for decoding")
            raise AudioSteganographyException(
                "Base file not set. Initialize with set_base_file() first."
            )

        logger.info(f"Starting WAV decoding from {self.base_file.full_path}")
        with open(self.base_file.full_path, "rb") as stream:
            self.decode_files_from_stream(stream)

    def _locate_head26(
        self, stream: BinaryIO, find_to: int, dsc_head26_version: str
    ) -> bool:
        """Locate the Head26 marker in the stream"""
        logger.debug(
            f"Locating head26 marker: version={dsc_head26_version}, limit={find_to}"
        )

        current_pos = stream.tell()
        stream.seek(0, 2)
        stream_length = stream.tell()
        stream.seek(current_pos)

        if find_to > stream_length or find_to == -1:
            find_to = stream_length

        buffer = stream.read(find_to)
        stream.seek(current_pos)

        self.decode_quality_mode = EncodeMode.NORMAL_QUALITY

        for i in range(len(buffer) - 104):
            test_block = buffer[i : i + 104]
            decoded = self.decode_data(test_block, 104)

            try:
                version_str = decoded[0:4].decode("ascii", errors="ignore")
                if version_str == dsc_head26_version:
                    quality_byte = decoded[4]
                    encrypt_byte = decoded[5]

                    if quality_byte in (2, 4, 8) and encrypt_byte in (0, 1):
                        stream.seek(current_pos + i)
                        logger.info(f"Found head26 marker at offset {current_pos + i}")
                        return True
            except Exception as e:
                logger.debug(f"Error checking block at offset {current_pos + i}: {e}")
                continue
        return False

    def analyze_stream(self, stream: BinaryIO, dsc_head26_version: str) -> bool:
        """Analyze a stream for hidden data"""
        logger.info(f"Analyzing stream for version {dsc_head26_version}")
        self.secret_files_info_items.clear()

        if not self._locate_head26(
            stream, self.OTHER_HEAD26_TRY_FIND_LIMIT, dsc_head26_version
        ):
            logger.debug("No head26 marker found in stream")
            return False

        initial_buffer = bytearray(stream.read(224))
        stream.seek(-224, 1)

        self.decode_quality_mode = EncodeMode.NORMAL_QUALITY
        initial_decoded = self.decode_data(bytes(initial_buffer), 224)

        try:
            version_str = initial_decoded[0:4].decode("ascii", errors="ignore")
        except Exception as e:
            logger.warning(f"Failed to decode version string: {e}")
            return False

        if version_str != dsc_head26_version:
            logger.debug(
                f"Version mismatch: expected {dsc_head26_version}, got {version_str}"
            )
            return False

        quality_byte = initial_decoded[4]
        encrypt_byte = initial_decoded[5]

        if quality_byte not in (2, 4, 8) or encrypt_byte not in (0, 1):
            logger.warning(
                f"Invalid header bytes: quality={quality_byte}, encrypt={encrypt_byte}"
            )
            return False

        is_encrypted = encrypt_byte == 1
        self.decode_quality_mode = EncodeMode(quality_byte)

        if is_encrypted:
            kdf_version_byte = initial_decoded[6]

            if kdf_version_byte == self.KDF_VERSION_ARGON2ID:
                buffer = bytearray(stream.read(224))
                decoded = self.decode_data(bytes(buffer), 224)

                self.kdf_version = self.KDF_VERSION_ARGON2ID
                self.salt = bytes(decoded[7:23])
                stored_key_verif = bytes(decoded[23:56])

                logger.info(
                    f"Found Argon2id header: quality={self.decode_quality_mode.name}, salt={self.salt.hex()[:16]}..."
                )
            else:
                buffer = bytearray(stream.read(104))
                decoded = self.decode_data(bytes(buffer), 104)

                self.kdf_version = self.KDF_VERSION_LEGACY
                self.salt = None
                stored_key_verif = bytes(decoded[6:26])

                logger.info(
                    f"Found legacy header: quality={self.decode_quality_mode.name}"
                )
        else:
            buffer = bytearray(stream.read(24))
            decoded = self.decode_data(bytes(buffer), 24)

            self.kdf_version = self.KDF_VERSION_LEGACY
            self.salt = None
            stored_key_verif = None

            logger.info(
                f"Found unencrypted header: quality={self.decode_quality_mode.name}"
            )

        logger.info(
            f"Found valid header: quality={self.decode_quality_mode.name}, encrypted={is_encrypted}, kdf_version={self.kdf_version if is_encrypted else 'N/A'}"
        )

        if is_encrypted:
            self.encrypt = True

            if (
                not self.key_verif_block
                or bytes(self.key_verif_block) != stored_key_verif
            ):
                logger.info(
                    f"Password required for encrypted content (KDF v{self.kdf_version})"
                )
                args = KeyRequiredEventArgs(h22_version=dsc_head26_version)

                if self.on_key_required:
                    self.on_key_required(args)

                if args.cancel:
                    logger.info("Key entry cancelled by user")
                    raise KeyEnterCanceledException()

                if self.kdf_version == self.KDF_VERSION_ARGON2ID:
                    logger.info("Using Argon2id key derivation (detected from header)")
                    self.set_key_argon(args.key)
                    logger.debug(
                        f"Derived Argon2id key with header salt: {self.salt.hex()[:16] if self.salt else None}..."
                    )

                elif self.kdf_version == self.KDF_VERSION_LEGACY:
                    logger.info(
                        "Using legacy Unicode key derivation (detected from header)"
                    )
                    self.set_key_unicode(args.key)
                else:
                    logger.error(f"Unknown KDF version: {self.kdf_version}")
                    raise AudioSteganographyException(
                        f"Unsupported KDF version: {self.kdf_version}"
                    )

                if bytes(self.key_verif_block) != stored_key_verif:
                    logger.error("Password verification failed")
                    raise AudioSteganographyException("Invalid password")

                logger.info("Password verified successfully")
        else:
            self.encrypt = False

        cipher = self._get_cipher() if is_encrypted else None

        file_count = 0
        while True:
            try:
                header_size = 32 * self.decode_quality_mode.value
                header_buffer = stream.read(header_size)

                if len(header_buffer) < header_size:
                    break

                decoded_header = self.decode_data(header_buffer, header_size)

                if is_encrypted and cipher:
                    decoded_header = bytearray(cipher.decrypt(bytes(decoded_header)))

                header_str = decoded_header[0:4].decode("ascii", errors="ignore")

                if header_str == self.H32_VERSION_DSSF:
                    item = SecretFileInfoItem("")
                    item.start_position = stream.tell()

                    file_name_bytes = decoded_header[4:24]
                    file_name = (
                        file_name_bytes.decode("ascii", errors="replace")
                        .rstrip("\x00")
                        .replace("?", "X")
                    )
                    if not file_name:
                        file_name = "unnamed"
                    item.full_path = file_name
                    item.file_name = file_name

                    item.file_size = struct.unpack(">I", bytes(decoded_header[24:28]))[
                        0
                    ]

                    stream.seek(item.file_size * self.decode_quality_mode.value, 1)
                    item.end_position = stream.tell()

                    padding = 16 - (item.file_size + 4) % 16
                    seek_back = -(16 - (4 + padding))
                    stream.seek(seek_back * self.decode_quality_mode.value, 1)

                    end_marker = stream.read(16 * self.decode_quality_mode.value)
                    decoded_end = self.decode_data(end_marker, len(end_marker))

                    if is_encrypted and cipher:
                        decoded_end = bytearray(cipher.decrypt(bytes(decoded_end)))

                    end_str = decoded_end.decode("ascii", errors="ignore")
                    if "DSSF" in end_str:
                        item.is_in_add_list = False
                        self.secret_files_info_items.append(item)
                        file_count += 1
                        logger.debug(
                            f"Found hidden file {file_count}: {item.file_name} ({item.file_size} bytes)"
                        )
                        continue
            except Exception as e:
                logger.debug(f"Error reading file header: {e}")
                break

        logger.info(f"Analysis complete: found {file_count} hidden files")
        return True

    def analyze_wav(self, wav_file_name: str) -> CarrierFileInfo:
        """Analyze a WAV file for hidden data"""
        logger.info(f"Analyzing WAV file: {wav_file_name}")
        info = CarrierFileInfo(file_name=wav_file_name)

        with WavFile(
            wav_file_name,
            0,
            EncodeMode.NORMAL_QUALITY,
            None,
            False,
            kdf_version=self.kdf_version,
            salt=self.salt,
        ) as wav_file:
            start_pos = wav_file.file_stream.tell()

            if self.analyze_stream(wav_file.file_stream, self.H22_VERSION_DSC2):
                info.h22_version = self.H22_VERSION_DSC2
                logger.info("File contains DSC2 hidden data")
            else:
                wav_file.file_stream.seek(start_pos)
                if self.analyze_stream(wav_file.file_stream, self.H22_VERSION_DSCF):
                    info.h22_version = self.H22_VERSION_DSCF
                    logger.info("File contains DSCF hidden data")
                else:
                    logger.info("No hidden data found in file")

            info.wav_head_length = len(wav_file.head)
            logger.debug(f"WAV header length: {info.wav_head_length} bytes")

        self.base_file_info = info
        return info
