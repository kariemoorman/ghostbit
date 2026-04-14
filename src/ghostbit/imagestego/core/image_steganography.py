#!/usr/bin/env python3
import os
import re
import zlib
import struct
import base64
import random
import secrets
import logging
import hashlib
from PIL import Image
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union, Any
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger("ghostbit.imagestego")


class Algorithm(IntEnum):
    """Steganography algorithm identifiers"""

    NONE = 0x00
    LSB = 0x01
    DCT = 0x02
    DWT = 0x03
    PALETTE = 0x04
    SVG_XML = 0x05


class ImageSteganographyException(Exception):
    """Base exception for steganography operations"""

    pass


@dataclass
class SecretFileInfoItem:
    """Information about a secret file"""

    full_path: str
    is_in_add_list: bool = False
    file_size: int = 0
    start_position: int = 0
    end_position: int = 0
    file_data: Optional[bytes] = None

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


class BaseStego:
    """Base class for steganography algorithms"""

    MAGIC = b"STGX"
    VERSION = 2
    SALT_SIZE = 16
    NONCE_SIZE = 12

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key using Argon2id"""
        kdf = Argon2id(salt=salt, length=32, iterations=3, lanes=4, memory_cost=65536)
        return kdf.derive(password.encode("utf-8"))

    def _encrypt_data(self, data: bytes, password: str) -> Tuple[bytes, bytes, bytes]:
        """Encrypt data using AES-256-GCM"""
        salt = secrets.token_bytes(self.SALT_SIZE)
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        key = self._derive_key(password, salt)

        aesgcm = AESGCM(key)
        key_commitment = hashlib.sha256(key).digest()
        ciphertext = aesgcm.encrypt(nonce, data, key_commitment)

        return salt, nonce, ciphertext

    def _decrypt_data(
        self, ciphertext: bytes, password: str, salt: bytes, nonce: bytes
    ) -> bytes:
        """Decrypt data using AES-256-GCM"""
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)
        key_commitment = hashlib.sha256(key).digest()

        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, key_commitment)
            return plaintext
        except Exception:
            raise ImageSteganographyException(
                "Decryption failed - incorrect password or corrupted data"
            )

    def build_payload(
        self,
        secret_files: List[SecretFileInfoItem],
        algorithm: Algorithm,
        password: Optional[str] = None,
    ) -> bytes:
        """Build payload with header and optional encryption"""

        payload_parts = []

        logger.debug(f"Building payload with {len(secret_files)} files")
        print("\n🔄 Building payload...")

        for idx, secret_file in enumerate(secret_files):

            logger.info(
                f"Encoding file {idx}/{len(secret_files)}: {secret_file.file_name}"
            )

            logger.debug("Retrieving filename components")
            file_name = os.path.basename(secret_file.full_path)
            base_name, ext = os.path.splitext(file_name)

            if len(ext) > 5:
                logger.debug("Truncating extension to max 5 chars (including dot)")
                ext = ext[:5]

            max_base_len = 20 - len(ext)
            if len(base_name) > max_base_len:
                base_name = base_name[:max_base_len]
                logger.info("Truncating secret file name")
                print(f"   • Truncating filename: {base_name}{ext}")

            full_name = base_name + ext

            with open(secret_file.full_path, "rb") as f:
                file_data = f.read()

                full_name_bytes = full_name.encode("utf-8", errors="replace")
                full_name_bytes = full_name_bytes.ljust(20, b"\x00")

                header = b"IMGF" + full_name_bytes + struct.pack(">I", len(file_data))

            logger.debug(
                f"Header created: magic=IMGF, name={full_name}, size={len(file_data)}"
            )

            payload_parts.append(header + file_data)
            logger.debug(f"  • Added part: {len(header + file_data)} bytes")

        combined_data = b"".join(payload_parts)

        logger.debug(f"Combined data (before end marker): {len(combined_data)} bytes")
        print(f"   • Combined: {len(combined_data)} bytes")

        combined_data += b"IMGF"

        logger.debug(f"Combined data (with end marker): {len(combined_data)} bytes")
        print(f"   • With end marker: {len(combined_data)} bytes")

        compressed = zlib.compress(combined_data, level=9)

        logger.debug(f"Compressed data: {len(compressed)} bytes")
        print(f"   • Compressed: {len(compressed)} bytes")

        if password:
            salt, nonce, ciphertext = self._encrypt_data(compressed, password)
            logger.debug(
                f"Encrypted: salt={len(salt)}, nonce={len(nonce)}, ciphertext={len(ciphertext)}"
            )
            print(f"   • Encrypted: {len(ciphertext)} bytes\n")
            payload = (
                self.MAGIC
                + struct.pack("B", self.VERSION)
                + struct.pack("B", algorithm)
                + struct.pack("B", 1)
                + salt
                + nonce
                + struct.pack(">I", len(ciphertext))
                + ciphertext
            )
        else:
            payload = (
                self.MAGIC
                + struct.pack("B", self.VERSION)
                + struct.pack("B", algorithm)
                + struct.pack("B", 0)
                + struct.pack(">I", len(compressed))
                + compressed
            )

        return payload

    def parse_payload(
        self, payload: bytes, password: Optional[str] = None
    ) -> Tuple[List[SecretFileInfoItem], Algorithm]:
        """Parse payload and decrypt if necessary"""

        logger.debug(f"Parsing payload: {len(payload)} bytes")

        if len(payload) < 8:
            raise ImageSteganographyException("Invalid payload - too short")

        magic = payload[:4]
        if magic != self.MAGIC:
            raise ImageSteganographyException("Invalid payload - magic number mismatch")

        version = payload[4]
        if version != self.VERSION:
            raise ImageSteganographyException(f"Unsupported version: {version}")

        algorithm = Algorithm(payload[5])
        encrypted = payload[6]
        print(f"   • Encrypted: {bool(encrypted)}\n")
        if encrypted:
            if not password:
                raise ImageSteganographyException(
                    "Password required - data is encrypted"
                )

            salt = payload[7 : 7 + self.SALT_SIZE]
            nonce = payload[7 + self.SALT_SIZE : 7 + self.SALT_SIZE + self.NONCE_SIZE]
            offset = 7 + self.SALT_SIZE + self.NONCE_SIZE
            data_length = struct.unpack(">I", payload[offset : offset + 4])[0]
            ciphertext = payload[offset + 4 : offset + 4 + data_length]

            compressed = self._decrypt_data(ciphertext, password, salt, nonce)

        else:
            offset = 7
            data_length = struct.unpack(">I", payload[offset : offset + 4])[0]
            compressed = payload[offset + 4 : offset + 4 + data_length]

        try:
            combined_data = zlib.decompress(compressed)
            logger.debug(f"Decompressed to {len(combined_data)} bytes")
        except zlib.error:
            raise ImageSteganographyException(
                "Data decompression failed - corrupted data"
            )

        extracted_files = []
        position = 0

        while position < len(combined_data):
            if combined_data[
                position : position + 4
            ] == b"IMGF" and position + 4 >= len(combined_data):
                logger.debug("Found end marker")
                break

            if len(combined_data) - position < 28:  # 4 (magic) + 20 (name) + 4 (size)
                break

            header_magic = combined_data[position : position + 4]
            if header_magic != b"IMGF":
                logger.warning(f"Invalid file header at position {position}")
                break

            file_name_bytes = combined_data[position + 4 : position + 24]
            file_name = (
                file_name_bytes.decode("ascii", errors="replace")
                .rstrip("\x00")
                .replace("?", "X")
            )
            if not file_name:
                file_name = "unnamed"

            file_size = struct.unpack(
                ">I", combined_data[position + 24 : position + 28]
            )[0]

            position += 28

            file_data = combined_data[position : position + file_size]
            position += file_size

            item = SecretFileInfoItem(
                full_path=file_name,
                is_in_add_list=False,
                file_size=file_size,
                file_data=file_data,
            )

            extracted_files.append(item)
            logger.debug(f"Parsed file: {file_name} ({file_size} bytes)")

        logger.info(f"Parsed {len(extracted_files)} files from payload")
        return extracted_files, algorithm


class LSBStego(BaseStego):
    """LSB steganography for lossless formats"""

    SEED_SIZE = 32  # 256 bits
    SEED_PIXELS = 86  # ceil(256 / 3 channels)

    def _write_seed_to_pixels(self, pixels: Any, width: int, height: int, seed: bytes) -> None:
        """Write shuffle seed into the first SEED_PIXELS pixels sequentially (LSB of RGB)."""
        bits = []
        for byte in seed:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)

        bit_idx = 0
        for pixel_idx in range(self.SEED_PIXELS):
            x = pixel_idx % width
            y = pixel_idx // width
            r, g, b, a = pixels[x, y]
            if bit_idx < len(bits):
                r = (r & 0xFE) | bits[bit_idx]
                bit_idx += 1
            if bit_idx < len(bits):
                g = (g & 0xFE) | bits[bit_idx]
                bit_idx += 1
            if bit_idx < len(bits):
                b = (b & 0xFE) | bits[bit_idx]
                bit_idx += 1
            pixels[x, y] = (r, g, b, a)

    def _read_seed_from_pixels(self, pixels: Any, width: int, height: int) -> bytes:
        """Read shuffle seed from the first SEED_PIXELS pixels sequentially (LSB of RGB)."""
        bits: list[int] = []
        total_bits = self.SEED_SIZE * 8

        for pixel_idx in range(self.SEED_PIXELS):
            x = pixel_idx % width
            y = pixel_idx // width
            r, g, b, a = pixels[x, y]
            if len(bits) < total_bits:
                bits.append(r & 1)
            if len(bits) < total_bits:
                bits.append(g & 1)
            if len(bits) < total_bits:
                bits.append(b & 1)

        seed_bytes = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte = (byte << 1) | bits[i + j]
            seed_bytes.append(byte)
        return bytes(seed_bytes)

    def _get_shuffled_coords(self, width: int, height: int, seed: bytes) -> list:
        """Get deterministically shuffled coordinates, excluding seed-reserved pixels."""
        seed_positions = set()
        for pixel_idx in range(self.SEED_PIXELS):
            seed_positions.add((pixel_idx % width, pixel_idx // width))

        coords = [
            (x, y) for y in range(height) for x in range(width)
            if (x, y) not in seed_positions
        ]

        seed_int = int.from_bytes(hashlib.sha256(seed).digest(), "big")
        rng = random.Random(seed_int)
        rng.shuffle(coords)
        return coords

    def get_capacity(self, cover_path_or_image: Union[str, Image.Image]) -> int:
        """Calculate maximum bytes that can be hidden using LSB (RGB channels only)"""
        logger.debug("Calculating LSB capacity")
        try:
            if isinstance(cover_path_or_image, Image.Image):
                img = cover_path_or_image.convert("RGB")
                width, height = img.size
                channels = len(img.getbands())
                return ((width * height - self.SEED_PIXELS) * min(channels, 3)) // 8
            else:
                with Image.open(cover_path_or_image).convert("RGB") as img:
                    width, height = img.size
                    channels = len(img.getbands())
                    return ((width * height - self.SEED_PIXELS) * min(channels, 3)) // 8
        except Exception as e:
            logger.error("Failed to calculate LSB capacity")
            raise ImageSteganographyException(f"Failed to calculate LSB capacity: {e}")

    def encode_seq(self, cover_path: str, data: bytes) -> Image.Image:
        """Embed data using LSB (memory-safe, RGBA, preserves size and metadata)"""
        try:
            with Image.open(cover_path) as image:
                img: Image.Image = image.convert("RGBA")
                width, height = img.size

                def bit_generator(data_bytes):
                    for byte in data_bytes:
                        for i in range(8):
                            yield (byte >> (7 - i)) & 1

                bits = bit_generator(data)
                pixels: Any = img.load()

                for y in range(height):
                    for x in range(width):
                        r, g, b, a = pixels[x, y]
                        try:
                            r = (r & 0xFE) | next(bits)
                        except StopIteration:
                            pass
                        try:
                            g = (g & 0xFE) | next(bits)
                        except StopIteration:
                            pass
                        try:
                            b = (b & 0xFE) | next(bits)
                        except StopIteration:
                            pass
                        pixels[x, y] = (r, g, b, a)

                return img

        except Exception as e:
            raise ImageSteganographyException(f"Failed to encode image: {e}")

    def encode(self, cover_path_or_image: Union[str, Image.Image], data: bytes) -> Image.Image:
        """Embed data using random LSB. Accepts file path or PIL Image."""
        try:
            if isinstance(cover_path_or_image, Image.Image):
                logger.info("Encoding from PIL Image object")
                img: Image.Image = cover_path_or_image.convert("RGBA")
            else:
                logger.info(f"Opening cover image: {cover_path_or_image}")
                img = Image.open(cover_path_or_image).convert("RGBA")

            width, height = img.size
            pixels: Any = img.load()
            logger.debug(f"Image size: {width}x{height}, mode: {img.mode}")

            total_bits = len(data) * 8
            logger.info(f"Embedding {len(data)} bytes ({total_bits} bits)")

            def bit_generator(data_bytes):
                for byte in data_bytes:
                    for i in range(8):
                        yield (byte >> (7 - i)) & 1

            logger.debug("Converting data to a bit generator")
            bits = bit_generator(data)

            logger.debug("Generating and embedding shuffle seed")
            seed = secrets.token_bytes(self.SEED_SIZE)
            self._write_seed_to_pixels(pixels, width, height, seed)

            logger.debug("Generating shuffled coordinates")
            coords = self._get_shuffled_coords(width, height, seed)
            logger.debug(f"Shuffled {len(coords)} pixel coordinates with seed")

            logger.debug("Embedding bits into pixels")
            bit_count = 0
            for idx, (x, y) in enumerate(coords):
                r, g, b, a = pixels[x, y]
                for channel_name, channel_value in zip(["R", "G", "B"], [r, g, b]):
                    try:
                        bit = next(bits)
                        if channel_name == "R":
                            r = (r & 0xFE) | bit
                        elif channel_name == "G":
                            g = (g & 0xFE) | bit
                        else:  # B
                            b = (b & 0xFE) | bit
                        bit_count += 1
                    except StopIteration:
                        break
                pixels[x, y] = (r, g, b, a)

                if bit_count >= total_bits:
                    logger.debug(f"All bits embedded at pixel index {idx}")
                    break

            logger.info(f"Finished embedding {bit_count} bits into image")
            return img

        except Exception as e:
            logger.error(f"Failed to encode image: {e}", exc_info=True)
            raise ImageSteganographyException(f"Failed to encode image: {e}")

    def decode(self, stego_image: Union[str, Image.Image], data_length: int) -> bytes:
        """Decode data hidden with random LSB embedding. Accepts file path or PIL Image."""
        try:
            if isinstance(stego_image, Image.Image):
                logger.info("Decoding from PIL Image object")
                img: Image.Image = stego_image.convert("RGBA")
            else:
                logger.info(f"Opening stego image: {stego_image}")
                img = Image.open(stego_image).convert("RGBA")

            width, height = img.size
            logger.debug(f"Image size: {width}x{height}, mode: {img.mode}")

            pixels: Any = img.load()
            total_bits = data_length * 8
            logger.info(f"Expecting {total_bits} bits ({data_length} bytes)")

            seed = self._read_seed_from_pixels(pixels, width, height)
            logger.debug("Read shuffle seed from image")
            coords = self._get_shuffled_coords(width, height, seed)
            logger.debug(f"Shuffled {len(coords)} pixel coordinates with seed")

            bits: list[int] = []
            for idx, (x, y) in enumerate(coords):
                r, g, b, a = pixels[x, y]
                if len(bits) < total_bits:
                    bits.append(r & 1)
                if len(bits) < total_bits:
                    bits.append(g & 1)
                if len(bits) < total_bits:
                    bits.append(b & 1)
                if len(bits) >= total_bits:
                    logger.debug(
                        f"Collected all {total_bits} bits at pixel index {idx}"
                    )
                    break

            data_bytes = bytearray()
            for i in range(0, len(bits), 8):
                byte = 0
                for j in range(8):
                    if i + j < len(bits):
                        byte = (byte << 1) | bits[i + j]
                data_bytes.append(byte)
            logger.info(f"Decoded {len(data_bytes)} bytes from image")

            return bytes(data_bytes)

        except Exception as e:
            logger.error(f"Failed to decode image: {e}", exc_info=True)
            raise ImageSteganographyException(f"Failed to decode image: {e}")

        except Exception as e:
            logger.error(f"Failed to decode image: {e}", exc_info=True)
            raise ImageSteganographyException(f"Failed to decode image: {e}")

    def decode_seq(self, stego_image: str, data_length: int) -> bytes:
        """Extract data using LSB"""
        try:
            image = Image.open(stego_image)
        except Exception as e:
            raise ImageSteganographyException(f"Failed to load image: {e}")

        img = image.convert("RGB")
        pixels = list(img.getdata())

        bits_needed = data_length * 8
        bits: List[str] = []

        for pixel in pixels:
            if len(bits) >= bits_needed:
                break
            r, g, b = pixel
            bits.append(str(r & 1))
            bits.append(str(g & 1))
            bits.append(str(b & 1))

        bits_str = "".join(bits[:bits_needed])
        data = bytearray()
        for i in range(0, len(bits_str), 8):
            byte = bits_str[i : i + 8]
            data.append(int(byte, 2))
        image.close()
        return bytes(data)


class PaletteStego(BaseStego):
    """GIF steganography using palette LSB embedding, for static and animated GIFs"""

    def get_capacity(self, gif_path: str) -> int:
        """Calculate maximum bytes that can be hidden in GIF"""

        if not os.path.exists(gif_path):
            raise ImageSteganographyException(f"GIF not found: {gif_path}")

        try:
            img: Image.Image
            with Image.open(gif_path) as img:
                if img.format != "GIF":
                    raise ImageSteganographyException("Not a GIF file")

                n_frames = getattr(img, "n_frames", 1)
                is_animated = n_frames > 1

                logger.debug(
                    f"Calculating capacity for {'animated' if is_animated else 'static'} GIF ({n_frames} frames)"
                )

                if is_animated:
                    total_bits = 0
                    global_palette = None

                    for frame_idx in range(n_frames):
                        img.seek(frame_idx)

                        logger.debug(f"Frame {frame_idx}: mode={img.mode}")

                        if img.mode == "P":
                            palette = img.getpalette()
                            if palette:
                                global_palette = palette
                                bits_in_frame = len(palette)
                                total_bits += bits_in_frame
                                logger.debug(
                                    f"Frame {frame_idx}: {bits_in_frame} palette bits (local)"
                                )
                            elif global_palette:
                                bits_in_frame = len(global_palette)
                                total_bits += bits_in_frame
                                logger.debug(
                                    f"Frame {frame_idx}: {bits_in_frame} palette bits (global)"
                                )
                            else:
                                logger.warning(
                                    f"Frame {frame_idx}: no palette available"
                                )

                    capacity_bytes = total_bits // 8
                    logger.info(
                        f"Animated GIF capacity: {capacity_bytes} bytes ({total_bits} bits from {n_frames} frames)"
                    )
                    return capacity_bytes
                else:
                    if img.mode != "P":
                        img = img.convert(
                            "P", palette=Image.Palette.ADAPTIVE, colors=256
                        )

                    palette = img.getpalette()
                    if not palette:
                        logger.warning("Static GIF has no palette")
                        return 0

                    capacity_bytes = len(palette) // 8
                    logger.info(f"Static GIF capacity: {capacity_bytes} bytes")
                    return capacity_bytes

        except Exception as e:
            raise ImageSteganographyException(f"Error calculating GIF capacity: {e}")

    def encode(self, gif_path: str, payload: bytes) -> List[Image.Image]:
        """Embed payload into GIF using palette LSB"""
        if not os.path.exists(gif_path):
            raise ImageSteganographyException(f"GIF not found: {gif_path}")

        try:
            with Image.open(gif_path) as img:
                if img.format != "GIF":
                    raise ImageSteganographyException("Not a GIF file")

                n_frames = getattr(img, "n_frames", 1)
                is_animated = n_frames > 1

                logger.debug("Converting payload to bits")
                bits = "".join(format(byte, "08b") for byte in payload)

                logger.debug("Checking capacity")
                capacity = self.get_capacity(gif_path)
                if len(payload) > capacity:
                    raise ImageSteganographyException(
                        f"Payload too large for GIF. Max: {capacity} bytes, Need: {len(payload)} bytes"
                    )
                logger.debug("Generating encoded GIF")
                if is_animated:
                    result = self._encode_animated(img, bits, n_frames)
                    return result
                else:
                    result = [self._encode_static(img, bits)]
                    return result

        except Exception as e:
            if isinstance(e, ImageSteganographyException):
                raise
            raise ImageSteganographyException(f"GIF encoding failed: {e}")

    def _encode_static(self, img: Image.Image, bits: str) -> Image.Image:
        """Encode data into static GIF"""
        if img.mode != "P":
            img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
            logger.debug("Image frame converted to palette mode")

        logger.debug("Retrieving palette and converting to list for modification")
        palette = list(img.getpalette() or [])

        logger.debug("Embedding bits in palette LSBs")
        bit_idx = 0
        for i in range(len(palette)):
            if bit_idx < len(bits):
                palette[i] = (palette[i] & 0xFE) | int(bits[bit_idx])
                bit_idx += 1
            else:
                break

        logger.debug("Creating new image with modified palette")
        result = img.copy()
        result.putpalette(palette)
        logger.info(f"Embedded {bit_idx} bits into static GIF palette")
        return result

    def _encode_animated(
        self, img: Image.Image, bits: str, n_frames: int
    ) -> List[Image.Image]:
        """Encode data into animated GIF"""
        frames = []
        bit_idx = 0
        global_palette = None

        logger.debug(
            f"Starting animated encoding: {len(bits)} bits across {n_frames} frames"
        )

        for frame_idx in range(n_frames):
            img.seek(frame_idx)
            frame = img.copy()

            if frame.mode != "P":
                frame = frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)

            palette = frame.getpalette()
            if palette:
                global_palette = palette
                logger.debug(
                    f"Frame {frame_idx}: has local palette ({len(palette)} values)"
                )
            elif global_palette:
                palette = global_palette
                logger.debug(
                    f"Frame {frame_idx}: using global palette ({len(palette)} values)"
                )
            else:
                logger.warning(f"Frame {frame_idx}: no palette available, skipping")
                frames.append(frame)
                continue

            palette = list(palette)
            bits_before = bit_idx

            for i in range(len(palette)):
                if bit_idx < len(bits):
                    palette[i] = (palette[i] & 0xFE) | int(bits[bit_idx])
                    bit_idx += 1
                else:
                    break

            bits_embedded = bit_idx - bits_before
            logger.debug(
                f"Frame {frame_idx}: embedded {bits_embedded} bits (total: {bit_idx}/{len(bits)})"
            )

            frame.putpalette(palette)
            frames.append(frame)

            if bit_idx >= len(bits):
                logger.info(f"All bits embedded by frame {frame_idx}")

                for remaining_idx in range(frame_idx + 1, n_frames):
                    img.seek(remaining_idx)
                    frames.append(img.copy())
                break

        if bit_idx < len(bits):
            logger.error(f"Only embedded {bit_idx}/{len(bits)} bits!")
            raise ImageSteganographyException(
                f"Failed to embed all data. Embedded {bit_idx}/{len(bits)} bits. "
                f"This suggests a capacity calculation error."
            )

        logger.info(f"Successfully embedded {bit_idx} bits across {len(frames)} frames")
        return frames

    def decode(self, gif_path: str) -> bytes | None:
        """Extract full payload from GIF"""
        if not os.path.exists(gif_path):
            raise ImageSteganographyException(f"GIF not found: {gif_path}")

        logger.info("GIF decode: extracting payload")

        try:
            all_bits = self._extract_all_bits(gif_path)
            logger.debug(f"Extracted {len(all_bits)} total bits from GIF")

            if len(all_bits) < 64:
                raise ImageSteganographyException(
                    f"Not enough data for header. Need 64 bits, found {len(all_bits)}"
                )

            header_data = self._bits_to_bytes(all_bits[:64])
            logger.debug("Extracted header data from GIF")

            if header_data[:4] != self.MAGIC:
                logger.debug(
                    f"No hidden data found in GIF - invalid magic number. Expected {self.MAGIC.hex()}, got {header_data[:4].hex()}"
                )
                return None

            version = header_data[4]
            algorithm = Algorithm(header_data[5])
            encrypted = header_data[6]

            logger.debug(
                f"Header: version={version}, algorithm={algorithm.name}, encrypted={encrypted}"
            )

            if encrypted:
                payload_offset = 7 + self.SALT_SIZE + self.NONCE_SIZE
            else:
                payload_offset = 7

            length_start_bit = payload_offset * 8
            length_end_bit = length_start_bit + 32

            if len(all_bits) < length_end_bit:
                raise ImageSteganographyException(
                    f"Not enough data for length field. Need {length_end_bit} bits, found {len(all_bits)}"
                )

            length_data = self._bits_to_bytes(all_bits[length_start_bit:length_end_bit])
            data_length = struct.unpack(">I", length_data)[0]
            logger.info(f"Detected payload size: {data_length} bytes")

            total_length = payload_offset + 4 + data_length
            total_bits_needed = total_length * 8

            if len(all_bits) < total_bits_needed:
                raise ImageSteganographyException(
                    f"Not enough data in GIF. Need {total_bits_needed} bits, found {len(all_bits)}"
                )

            logger.info(f"Extracting {total_length} total bytes from GIF")
            full_payload = self._bits_to_bytes(all_bits[:total_bits_needed])
            logger.info("GIF decoding complete")

            return full_payload

        except Exception as e:
            raise ImageSteganographyException(f"GIF decoding failed: {e}")

    def _extract_all_bits(self, gif_path: str) -> List[int]:
        """Extract bits from GIF"""
        with Image.open(gif_path) as img:
            if img.format != "GIF":
                raise ImageSteganographyException("Not a GIF file")

            try:
                n_frames = getattr(img, "n_frames", 1)
                all_bits = []

                img.seek(0)
                global_palette = img.getpalette() if img.mode == "P" else None
                logger.debug(
                    f"Global palette: {len(global_palette) if global_palette else 0} values"
                )

                for frame_idx in range(n_frames):
                    img.seek(frame_idx)

                    if img.mode != "P":
                        logger.debug(
                            f"Frame {frame_idx} not in palette mode (mode: {img.mode})"
                        )
                        continue

                    palette = img.getpalette()

                    if not palette and global_palette:
                        palette = global_palette
                        logger.debug(f"Frame {frame_idx}: using global palette")
                    elif palette:
                        logger.debug(
                            f"Frame {frame_idx}: has local palette ({len(palette)} values)"
                        )
                    else:
                        logger.debug(f"Frame {frame_idx}: no palette available")
                        continue

                    if len(palette) == 0:
                        logger.debug(f"Frame {frame_idx}: palette is empty!")
                        continue

                    try:
                        frame_bits = [palette[i] & 1 for i in range(len(palette))]
                        all_bits.extend(frame_bits)
                        logger.debug(
                            f"Frame {frame_idx}: extracted {len(frame_bits)} bits"
                        )
                    except Exception as e:
                        logger.error(f"Frame {frame_idx}: extraction failed - {e}")
                        continue

                logger.info(
                    f"Total extracted: {len(all_bits)} bits from {n_frames} frames"
                )

                if len(all_bits) == 0:
                    raise ImageSteganographyException(
                        "No bits could be extracted from GIF!"
                    )

                return all_bits

            except Exception as e:
                raise ImageSteganographyException(
                    f"Error extracting bits from GIF: {e}"
                )

    def _bits_to_bytes(self, bits: List[int]) -> bytes:
        """Convert list of bits (integers 0 or 1) to bytes."""

        num_complete_bytes = len(bits) // 8
        bits_to_convert = bits[: num_complete_bytes * 8]

        if len(bits) % 8 != 0:
            logger.debug(
                f"Warning: {len(bits) % 8} extra bits ignored in conversion "
                f"(not a complete byte)"
            )

        return bytes(
            int("".join(str(bit) for bit in bits_to_convert[i : i + 8]), 2)
            for i in range(0, len(bits_to_convert), 8)
        )


class SVGStego(BaseStego):
    """SVG XML-based steganography"""

    def encode(self, svg_path: str, data: bytes) -> str:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()

        encoded = base64.b64encode(data).decode("ascii")
        hidden_comment = f"<!-- STGX:{encoded} -->"

        if "</svg>" in svg_content:
            svg_content = svg_content.replace("</svg>", f"{hidden_comment}\n</svg>")
        else:
            svg_content += hidden_comment
        logger.info("SVG encoding complete")
        return svg_content

    def decode(self, svg_path: str) -> bytes | None:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()

        match = re.search(r"<!--\s*STGX:([A-Za-z0-9+/=]+)\s*-->", svg_content)
        if not match:
            logger.debug("No hidden data found in SVG")
            return None

        encoded = match.group(1)

        try:
            return base64.b64decode(encoded)
        except Exception:
            raise ImageSteganographyException("Failed to decode hidden data")

    def get_capacity(self, image_path: str) -> int:
        original_size = os.path.getsize(image_path)
        size_based_limit = original_size * 10
        absolute_limit = 50 * 1024 * 1024
        capacity = min(size_based_limit, absolute_limit)
        capacity = max(capacity, 1 * 1024 * 1024)
        return capacity
