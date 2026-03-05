#!/usr/bin/env python3
import os
import sys
import time
import struct
import logging
import svgwrite
import numpy as np
from PIL import Image
from typing import Optional, List, Dict, Union, TypedDict, Any

from ghostbit.imagestego.core.image_statistics import (
    StatisticalAnalysis,
    ImageStatisticsException,
)
from ghostbit.imagestego.core.image_steganography import (
    Algorithm,
    LSBStego,
    SVGStego,
    BaseStego,
    PaletteStego,
    SecretFileInfoItem,
    ImageSteganographyException,
)

logger = logging.getLogger("ghostbit.imagestego")


class ImageMultiFormatCoderException(Exception):
    """Base exception for steganography operations"""

    pass


class ImageTestCreationException(Exception):
    """Base exception for image test file creation operations"""

    pass


class CapacityResult(TypedDict):
    format: str
    algorithm: str
    capacity_bytes: int
    capacity_kb: float
    capacity_mb: float


class AnalysisResult(TypedDict):
    has_hidden_data: bool
    format: str
    algorithm: Optional[Algorithm]
    encrypted: Optional[bool]


class ImageMultiFormatCoder(BaseStego):
    """Main controller with format detection and algorithm selection"""

    FORMAT_ALGORITHMS = {
        "PNG": Algorithm.LSB,
        "BMP": Algorithm.LSB,
        "TIFF": Algorithm.LSB,
        "JPEG": Algorithm.LSB,
        "JPG": Algorithm.LSB,
        "GIF": Algorithm.PALETTE,
        "WEBP": Algorithm.LSB,
        "AVIF": Algorithm.LSB,
        "HEIC": Algorithm.LSB,
        "SVG": Algorithm.SVG_XML,
    }

    def __init__(self) -> None:
        super().__init__()
        self.algorithms: Dict[Algorithm, Union[LSBStego, PaletteStego, SVGStego]] = {
            Algorithm.LSB: LSBStego(),
            # Algorithm.DCT: DCTStego(),
            # Algorithm.DWT: DWTStego(),
            Algorithm.PALETTE: PaletteStego(),
            Algorithm.SVG_XML: SVGStego(),
        }
        self.stats = StatisticalAnalysis()

    def detect_format(self, image_path: str) -> str:
        ext = os.path.splitext(image_path)[1].upper().lstrip(".")
        try:
            if ext == "SVG":
                return "SVG"
            else:
                with Image.open(image_path) as img:
                    return img.format or ext
        except Exception:
            return ext

    def select_algorithm(self, format: str) -> Algorithm:
        return self.FORMAT_ALGORITHMS.get(format, Algorithm.LSB)

    def calculate_capacity(self, image_path: str) -> CapacityResult:
        """Calculate hiding capacity for an image"""
        if not os.path.exists(image_path):
            raise ImageSteganographyException(f"Image not found: {image_path}")

        print(f"📁 Input File: '{os.path.basename(image_path)}'")
        format = self.detect_format(image_path)
        algorithm = self.select_algorithm(format)
        print(f"  • File Format: {format}")
        print(f"  • Algorithm Selected: {algorithm.name}")

        result: CapacityResult = {
            "format": format,
            "algorithm": algorithm.name,
            "capacity_bytes": 0,
            "capacity_kb": 0.0,
            "capacity_mb": 0.0,
        }

        try:
            stego = self.algorithms[algorithm]

            if hasattr(stego, "get_capacity"):
                capacity = stego.get_capacity(image_path)
            else:
                raise ImageSteganographyException(
                    f"Algorithm {algorithm.name} does not support capacity calculation"
                )

            result["capacity_bytes"] = capacity
            result["capacity_kb"] = capacity / 1024
            result["capacity_mb"] = capacity / (1024 * 1024)

            return result
        except Exception as e:
            raise ImageSteganographyException(f"Failed to calculate capacity: {e}")

    def analyze(self, image_path: str) -> AnalysisResult:
        """Analyze image for hidden data and print relevant statistics"""
        if not os.path.exists(image_path):
            raise ImageSteganographyException(f"Image not found: {image_path}")

        format = self.detect_format(image_path).upper()

        result: AnalysisResult = {
            "has_hidden_data": False,
            "format": format,
            "algorithm": None,
            "encrypted": None,
        }

        print(f"   Input File: '{os.path.basename(image_path)}'")
        print(f"   • Format: {format}")

        print("\n📊 Statistical Analysis:")

        try:
            if format == "GIF":
                stats = self.stats.analyze_gif(image_path)
                chi_stats = stats["chi_sq"]
                entropy_stats = stats["palette_entropy"]

                if not isinstance(chi_stats, dict):
                    raise ImageStatisticsException("Invalid chi_stats format")

                avg_palette = chi_stats.get("average_palette")
                avg_pixel = chi_stats.get("average_pixel")
                frames_palette = chi_stats.get("frames_palette")
                frames_pixel = chi_stats.get("frames_pixel")

                if not isinstance(avg_palette, (int, float)) or not isinstance(
                    avg_pixel, (int, float)
                ):
                    raise ImageStatisticsException("Invalid average values")

                if not isinstance(frames_palette, list) or not isinstance(
                    frames_pixel, list
                ):
                    raise ImageStatisticsException("Invalid frames data")

                print(
                    f"   • Chi-Square (avg): Palette - {avg_palette:.2f} {'(Low detection risk)' if avg_palette < 100 else '(Moderate detection risk)' if avg_palette < 300 else '(High detection risk)'}"
                    f", Pixel - {avg_pixel:.4f} {'(Low detection risk)' if avg_pixel < .1 else '(Moderate detection risk)' if avg_pixel < .3 else '(High detection risk)'}"
                )
                print("   • Chi-Square (per frame):")
                for idx, chi in enumerate(frames_palette):
                    palette_risk = (
                        "(High detection risk)"
                        if chi > 300
                        else (
                            "(Moderate detection risk)"
                            if chi > 100
                            else "(Low detection risk)"
                        )
                    )
                    pixel_chi = frames_pixel[idx]
                    pixel_risk = (
                        "(High detection risk)"
                        if pixel_chi > 0.3
                        else (
                            "(Moderate detection risk)"
                            if pixel_chi > 0.1
                            else "(Low detection risk)"
                        )
                    )
                    print(
                        f"     • Frame {idx}: Palette - {chi:.2f} {palette_risk}, Pixel - {pixel_chi:.4f} {pixel_risk}"
                    )
                print(f"   • Entropy: Palette - {entropy_stats}")

            elif format == "SVG":
                stats = self.stats.analyze_svg(image_path)
                entropy = stats["entropy"]
                suspicious_patterns = stats["suspicious_patterns"]
                numerical_stats = stats["numeric_stats"]

                if not isinstance(entropy, (int, float)):
                    raise ImageStatisticsException("Invalid entropy value")

                if not isinstance(suspicious_patterns, dict) or not isinstance(
                    numerical_stats, dict
                ):
                    raise ImageStatisticsException("Invalid stats format")

                mean_val = numerical_stats.get("mean")
                variance_val = numerical_stats.get("variance")
                min_val = numerical_stats.get("min")
                max_val = numerical_stats.get("max")
                count_val = numerical_stats.get("count")

                print(
                    f"   • Entropy: {entropy:.6f} bits per byte "
                    f"{'(Low)' if entropy < 4 else '(Medium)' if entropy < 6 else '(High - suspicious)'}"
                )
                print(
                    f"   • Suspicious Patterns: { {k: v for k, v in suspicious_patterns.items() if v > 0} or 'None'}"
                )

                mean_str = (
                    f"{mean_val:.2f}" if isinstance(mean_val, (int, float)) else "N/A"
                )
                var_str = (
                    f"{variance_val:.2f}"
                    if isinstance(variance_val, (int, float))
                    else "N/A"
                )
                min_str = (
                    f"{min_val:.2f}" if isinstance(min_val, (int, float)) else "N/A"
                )
                max_str = (
                    f"{max_val:.2f}" if isinstance(max_val, (int, float)) else "N/A"
                )

                print(
                    f"   • Numerical Stats: count={count_val}, "
                    f"mean={mean_str}, variance={var_str}, "
                    f"min={min_str}, max={max_str}"
                )

            else:
                chi_stats = self.stats.analyze_lsb(image_path)
                chi_avg = chi_stats["average"]
                risk_level = (
                    "Low" if chi_avg < 100 else "Moderate" if chi_avg < 300 else "High"
                )
                print(
                    f"   • Chi-Square Average: {chi_avg:.2f} ({risk_level} detection risk)"
                )
                print(f"     • Chi-Square R: {chi_stats['R']:.2f}")
                print(f"     • Chi-Square G: {chi_stats['G']:.2f}")
                print(f"     • Chi-Square B: {chi_stats['B']:.2f}")

        except Exception as e:
            logger.debug(f"Could not perform statistical analysis: {e}")
            raise ImageStatisticsException(
                f"Statistics Calculation Error occurred: {e}"
            )

        try:
            algorithm = self.select_algorithm(format)
            if algorithm:
                stego = self.algorithms[algorithm]
                if algorithm.name != "LSB":
                    if not isinstance(stego, (PaletteStego, SVGStego)):
                        raise ImageSteganographyException(
                            "Expected PaletteStego or SVGStego instance"
                        )
                    if hasattr(stego, "decode"):
                        payload = stego.decode(image_path)
                    else:
                        raise ImageSteganographyException(
                            f"Algorithm {algorithm.name} does not support decoding"
                        )
                else:
                    if not isinstance(stego, LSBStego):
                        raise ImageSteganographyException("Expected LSBStego instance")
                    if hasattr(stego, "decode"):
                        payload = stego.decode(image_path, 8)
                    else:
                        raise ImageSteganographyException(
                            f"Algorithm {algorithm.name} does not support decoding"
                        )

                if not payload:
                    result["has_hidden_data"] = False
                else:
                    magic = payload[:4]
                    if magic == self.MAGIC:
                        result["has_hidden_data"] = True
                        result["algorithm"] = Algorithm(payload[5])
                        result["encrypted"] = bool(payload[6])

        except Exception as e:
            logger.debug(f"Error detecting hidden data: {e}")
            raise ImageSteganographyException(f"Error detecting hidden data: {e}")

        return result

    def generate_statistics(
        self,
        format: str,
        original_filepath: str,
        stego_filepath: str,
        stego_image: Union[Image.Image, str, List[Image.Image]],
    ) -> None:
        try:
            print("\n📊 Statistical Analysis:")
            if format == "GIF":
                psnr = self.stats.gif_calculate_psnr(original_filepath, stego_filepath)
                mse = self.stats.gif_calculate_mse(original_filepath, stego_filepath)
                chi_stats_delta = self.stats.gif_chi_square_delta(
                    original_filepath, stego_filepath
                )
                entropy_delta = self.stats.gif_entropy_delta(
                    original_filepath, stego_filepath
                )

                delta_pixel_avg = chi_stats_delta.get("delta_pixel_average")
                delta_palette_avg = chi_stats_delta.get("delta_palette_average")
                delta_palette_frames = chi_stats_delta.get("delta_palette_per_frame")
                max_abs_entropy = entropy_delta.get("max_abs")
                psnr_avg = psnr.get("psnr_average")
                mse_avg = mse.get("mse_average")

                if not isinstance(delta_pixel_avg, (int, float)) or not isinstance(
                    delta_palette_avg, (int, float)
                ):
                    raise ImageStatisticsException("Invalid chi-square delta values")

                if not isinstance(delta_palette_frames, list):
                    raise ImageStatisticsException("Invalid palette frames data")

                if not isinstance(max_abs_entropy, (int, float)):
                    raise ImageStatisticsException("Invalid entropy delta")

                if not isinstance(psnr_avg, (int, float)):
                    raise ImageStatisticsException("Invalid PSNR value")

                if not isinstance(mse_avg, (int, float)):
                    raise ImageStatisticsException("Invalid MSE value")

                print(
                    f"  • 𝚫 Chi-Square (avg): Pixel - {delta_pixel_avg:.4f} {'(Excellent - imperceptible)' if delta_pixel_avg < 1 else '(Moderate risk)' if delta_pixel_avg < 10 else '(High risk)'}"
                    f", Palette - {delta_palette_avg:.4f} {'(Excellent - imperceptible)' if delta_palette_avg < 100 else '(Moderate risk)' if delta_palette_avg < 300 else '(High risk)'}"
                )
                for idx, chi in enumerate(delta_palette_frames):
                    print(
                        f"    • 𝚫 Chi-Square Palette (Frame {idx}): {chi:.6f} {'(Excellent - imperceptible)' if chi < 100 else '(Moderate risk)' if chi < 300 else '(High risk)'}"
                    )
                print(
                    f"  • 𝚫 Entropy (avg): {max_abs_entropy:.4f} {'Excellent' if max_abs_entropy < 0.1 else '(Mild anomaly)' if max_abs_entropy < 0.3 else 'Suspicious'}"
                )
                print(
                    f"  • PSNR: {psnr_avg:.2f} dB {'(Excellent - imperceptible)' if psnr_avg > 40 else '(Good)' if psnr_avg > 30 else '(Detectable)'}"
                )
                print(
                    f"  • MSE (avg): {mse_avg:.4f} {'(Excellent - imperceptible)' if mse_avg < 1 else '(Good)' if mse_avg < 10 else '(Detectable)'}"
                )

            elif format == "SVG":
                results = self.stats.analyze_svg(stego_filepath)
                entropy = results["entropy"]
                suspicious_patterns = results["suspicious_patterns"]
                numerical_stats = results["numeric_stats"]
                delta = self.stats.compare_svgs(original_filepath, stego_filepath)

                if not isinstance(entropy, (int, float)):
                    raise ImageStatisticsException("Invalid entropy")

                if not isinstance(suspicious_patterns, dict) or not isinstance(
                    numerical_stats, dict
                ):
                    raise ImageStatisticsException("Invalid stats")

                if not isinstance(delta, dict):
                    raise ImageStatisticsException("Invalid delta")

                entropy_delta_val = delta.get("entropy_bytes_delta")
                if not isinstance(entropy_delta_val, (int, float)):
                    raise ImageStatisticsException("Invalid entropy delta")

                susp_delta = delta.get("suspicious_patterns_delta", {})
                num_delta = delta.get("numeric_stats_delta", {})

                if not isinstance(num_delta, dict):
                    raise ImageStatisticsException("Invalid numeric delta")

                print(
                    f"  • Entropy: {entropy:.6f} bits per byte {'(Low)' if entropy < 4 else '(Medium)' if entropy < 6 else '(High - suspicious)'}"
                    f"\n    • 𝚫 Entropy (bytes): {entropy_delta_val:.4f} {'(Low risk)' if entropy_delta_val < .2 else '(Medium risk)' if entropy_delta_val < .5 else '(High risk)'}"
                )
                print(
                    f"  • Suspicious Patterns: { {k: v for k, v in suspicious_patterns.items() if v > 0} or 'None'}"
                    f"\n    • 𝚫 Suspicious Patterns: {susp_delta}"
                )

                count = numerical_stats.get("count", 0)
                mean = numerical_stats.get("mean")
                variance = numerical_stats.get("variance")
                min_v = numerical_stats.get("min")
                max_v = numerical_stats.get("max")

                d_count = num_delta.get("count", 0)
                d_mean = num_delta.get("mean")
                d_variance = num_delta.get("variance")
                d_min = num_delta.get("min")
                d_max = num_delta.get("max")

                mean_str = f"{mean:.2f}" if isinstance(mean, (int, float)) else "N/A"
                var_str = (
                    f"{variance:.2f}" if isinstance(variance, (int, float)) else "N/A"
                )
                min_str = f"{min_v:.2f}" if isinstance(min_v, (int, float)) else "N/A"
                max_str = f"{max_v:.2f}" if isinstance(max_v, (int, float)) else "N/A"

                d_mean_str = (
                    f"{d_mean:.2f}" if isinstance(d_mean, (int, float)) else "N/A"
                )
                d_var_str = (
                    f"{d_variance:.2f}"
                    if isinstance(d_variance, (int, float))
                    else "N/A"
                )
                d_min_str = f"{d_min:.2f}" if isinstance(d_min, (int, float)) else "N/A"
                d_max_str = f"{d_max:.2f}" if isinstance(d_max, (int, float)) else "N/A"

                print(
                    f"  • Stats: count={count}, mean={mean_str}, variance={var_str}, min={min_str}, max={max_str}"
                    f"\n    • 𝚫 Stats: count={d_count}, mean={d_mean_str}, variance={d_var_str}, min={d_min_str}, max={d_max_str}"
                )
            elif format in ["JPG", "JPEG"]:
                pass
            else:
                if not isinstance(stego_image, Image.Image):
                    raise ImageStatisticsException(
                        "Invalid stego_image type for LSB statistics"
                    )

                psnr_val = self.stats.lsb_calculate_psnr(original_filepath, stego_image)
                mse_val = self.stats.lsb_calculate_mse(original_filepath, stego_image)
                hist_diff = self.stats.lsb_calculate_histogram_difference(
                    original_filepath, stego_image
                )
                chi_stats_delta = self.stats.lsb_chi_square_delta(
                    original_filepath, stego_filepath
                )

                delta_dict = chi_stats_delta.get("delta")
                if not isinstance(delta_dict, dict):
                    raise ImageStatisticsException("Invalid delta stats")

                chi_avg = delta_dict.get("average", 0.0)
                chi_med = delta_dict.get("median", 0.0)

                if not isinstance(chi_avg, (int, float)) or not isinstance(
                    chi_med, (int, float)
                ):
                    raise ImageStatisticsException("Invalid chi values")

                risk_level = (
                    "No"
                    if -100 < chi_avg < 10
                    else (
                        "Low"
                        if (-350 < chi_avg < -100 or 10 < chi_avg < 100)
                        else "Moderate" if chi_avg < 300 else "High"
                    )
                )
                print(f"  • 𝚫 Chi-Square (avg): {chi_avg:.4f} ({risk_level} risk)")
                print(
                    f"  • 𝚫 Chi-Square (median): {chi_med:.6f} {'(Low risk)' if (-350 < chi_med < -100 or 10 < chi_avg < 100) else '(Moderate risk)' if chi_med < 300 else '(High risk)'}"
                )
                for channel in ["R", "G", "B"]:
                    chi_val = delta_dict.get(channel, 0.0)

                    if not isinstance(chi_val, (int, float)):
                        continue

                    risk_level = (
                        "No"
                        if -100 < chi_val < 10
                        else (
                            "Low"
                            if chi_val < 100
                            else (
                                "Low"
                                if (-350 < chi_val < 100 and 10 < chi_avg < 100)
                                else (
                                    "Moderate"
                                    if (100 < chi_val < 300 or -1000 < chi_val < -350)
                                    else "High"
                                )
                            )
                        )
                    )

                    print(
                        f"     • 𝚫 Chi-Square - '{channel}': {chi_val:.4f} ({risk_level} risk)"
                    )

                print(
                    f"  • PSNR: {psnr_val:.2f} dB {'(Excellent - imperceptible)' if psnr_val > 40 else '(Good)' if psnr_val > 30 else '(Detectable)'}"
                )
                print(
                    f"  • MSE: {mse_val:.4f} {'(Excellent - imperceptible)' if mse_val < 1 else '(Good)' if mse_val < 10 else '(Detectable)'}"
                )

                avg_hist = hist_diff.get("average", 0.0)
                if isinstance(avg_hist, (int, float)):
                    print(
                        f"  • Histogram Difference: {avg_hist:.6f} {'(Excellent - imperceptible)' if avg_hist < 0.01 else '(Good)' if avg_hist < 0.05 else '(Detectable)'}"
                    )
        except Exception as e:
            logger.error("Error occurred during statistics calculations")
            raise ImageStatisticsException(f"Statistics Calculation Error: {e}")

    def encode(
        self,
        cover_path: str,
        secret_files: List[str],
        output_dir: str,
        password: Optional[str] = None,
        show_stats: bool = True,
    ) -> str:
        """Encode secret file with statistical analysis"""

        if not os.path.exists(cover_path):
            raise ImageSteganographyException(f"Cover image not found: {cover_path}")

        print(f"📁 Carrier File: {os.path.basename(cover_path)}")
        format = self.detect_format(cover_path)
        algorithm = self.select_algorithm(format)
        stego = self.algorithms[algorithm]

        print(f"   • File Format: {format}")
        print(f"   • Algorithm Selected: {algorithm.name}")

        secret_files_info_items: List[SecretFileInfoItem] = []
        for secret_file in secret_files:
            if not os.path.exists(secret_file):
                logger.warning(f"Secret file not found: {secret_file}")
                print(f"⚠️  Warning: {secret_file} not found, skipping...")
                continue
            print("\n🔄 Adding Secret Files...")
            info = SecretFileInfoItem(secret_file, is_in_add_list=True)
            secret_files_info_items.append(info)
            logger.info(
                f"Added secret file: '{info.file_name}' ({info.file_size} bytes)"
            )
            print(f"   • File: '{info.file_name}' ({info.file_size_mb})")

        if output_dir:
            logger.debug(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

        if not password:
            print(
                "⚠️  WARNING: Encoding without encryption! Data will not be password protected."
            )
            response = input("Continue without password? (y/N): ")
            if response.lower() != "y":
                print("Aborted.")
                sys.exit(0)

        cover_stem = os.path.splitext(os.path.basename(cover_path))[0]
        cover_ext = os.path.splitext(cover_path)[1]

        if cover_ext in [".jpg", ".jpeg"]:
            logger.debug(f"Converting '{cover_ext}' to '.png'")
            cover_ext = ".png"
            format = "PNG"

        output_filepath = f"{output_dir}/{cover_stem}_encoded{cover_ext}"

        logger.info(f"Building payload for {algorithm}")
        payload = stego.build_payload(secret_files_info_items, algorithm, password)

        logger.info("Calculating image capacity statistics")
        if hasattr(stego, "get_capacity"):
            capacity = stego.get_capacity(cover_path)
        else:
            raise ImageSteganographyException(
                f"Algorithm {algorithm.name} does not support capacity calculation"
            )

        capacity_remaining = capacity - len(payload)
        capacity_percent = (len(payload) / capacity) * 100

        if len(payload) > capacity:
            raise ImageSteganographyException(
                f"Secret file too large!\n"
                f"  Max capacity: {capacity:,} bytes\n"
                f"  Required: {len(payload):,} bytes\n"
                f"  Secret file: {len(payload):,} bytes"
            )

        try:
            logger.info(f"Processing {format} format")
            print("🔄 Encoding Secret Files...")

            if hasattr(stego, "encode"):
                stego_result = stego.encode(cover_path, payload)
            else:
                raise ImageSteganographyException(
                    f"Algorithm {algorithm.name} does not support encoding"
                )

            print(f"   ✓ Successfully hidden {len(payload):,} bytes")
            print("\n🔄 Creating Final Output...")
            print(f"   • Output File: '{output_filepath}'")

            if format == "SVG":
                if not isinstance(stego_result, str):
                    raise ImageSteganographyException("Invalid SVG result type")
                with open(output_filepath, "w", encoding="utf-8") as f:
                    f.write(stego_result)
                stego_image: Union[Image.Image, str, List[Image.Image]] = stego_result

            elif format == "GIF":
                if not isinstance(stego_result, list):
                    raise ImageSteganographyException("Invalid GIF result type")

                with Image.open(cover_path) as orig_gif:
                    n_frames = getattr(orig_gif, "n_frames", 1)
                    is_animated = n_frames > 1

                    if is_animated:
                        logger.info("Saving animated GIF")
                        duration = orig_gif.info.get("duration", 100)
                        loop = orig_gif.info.get("loop", 0)

                        verified_frames: List[Image.Image] = []
                        for i, frame in enumerate(stego_result):
                            if frame.mode != "P":
                                logger.debug(
                                    f"Frame {i} is {frame.mode}, converting to P"
                                )
                                frame = frame.convert(
                                    "P", palette=Image.Palette.ADAPTIVE, colors=256
                                )

                            if not frame.getpalette():
                                logger.error(
                                    f"Frame {i} has no palette after conversion!"
                                )
                                raise ImageSteganographyException(
                                    f"Frame {i} missing palette"
                                )

                            verified_frames.append(frame)

                        verified_frames[0].save(
                            output_filepath,
                            save_all=True,
                            append_images=verified_frames[1:],
                            duration=duration,
                            loop=loop,
                            optimize=False,
                            format="GIF",
                        )

                        logger.info(f"Saved animated GIF with {n_frames} frames")

                    else:
                        stego_result[0].save(
                            output_filepath, save_all=True, format="GIF", optimize=False
                        )
                        logger.info("Saved static GIF")

                stego_image = stego_result

            else:
                if not isinstance(stego_result, Image.Image):
                    raise ImageSteganographyException("Invalid image result type")

                save_kwargs: Dict[str, Any] = {}
                if format == "PNG":
                    save_kwargs = {"optimize": True}
                elif format == "WEBP":
                    save_kwargs = {"quality": 95, "lossless": True}
                stego_result.save(output_filepath, format=format, **save_kwargs)
                stego_image = stego_result

            print(f"   • Capacity Used: {capacity_percent:.2f}%")
            print(
                f"   • Remaining Capacity: {capacity_remaining:,} bytes ({(capacity_remaining/(1024 ** 2)):.2f} MB)"
            )
            print(
                f"   • Output File Size: {(os.path.getsize(output_filepath)/(1024 ** 2)):.2f} MB"
            )

            if show_stats:
                try:
                    self.generate_statistics(
                        format=format,
                        original_filepath=cover_path,
                        stego_filepath=output_filepath,
                        stego_image=stego_image,
                    )
                except Exception as e:
                    raise ImageMultiFormatCoderException(
                        f"Image statistics calculations failed: {e}"
                    )

            print("\n✅ Encoding Complete!\n")
            return output_filepath

        except Exception as e:
            raise ImageSteganographyException(f"Image encoding failed: {e}")

    def decode(
        self, stego_path: str, output_dir: str, password: Optional[str] = None
    ) -> int:
        """Decode secret file from stego image"""

        if not os.path.exists(stego_path):
            raise ImageSteganographyException(f"Stego image not found: {stego_path}")

        print(f"📁 Input File: '{os.path.basename(stego_path)}'")
        if output_dir:
            logger.debug(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

        try:
            print("\n🔍 Analyzing file...\n")
            format = self.detect_format(stego_path)
            algorithm = self.select_algorithm(format)
            stego = self.algorithms[algorithm]
        except Exception as e:
            raise ImageSteganographyException(f"Error detecting algorithm: {e}")

        try:
            logger.info(f"Processing {format} format")
            if algorithm.name not in ["LSB"]:
                if not isinstance(stego, (PaletteStego, SVGStego)):
                    raise ImageSteganographyException(
                        "Expected PaletteStego or SVGStego instance"
                    )

                if hasattr(stego, "decode"):
                    payload = stego.decode(stego_path)
                    if not payload:
                        logger.info("No hidden data found in file")
                        print("   ✗ No hidden data found")
                        print("\n✅ Decoding Complete!\n")
                        return 0
                    else:
                        logger.info("Hidden data found in file")
                        print("   Hidden Data Found!")
                        print(f"   • Algorithm detected: {algorithm.name}")
                else:
                    raise ImageSteganographyException(
                        f"Algorithm {algorithm.name} does not support decoding"
                    )

                try:
                    extracted_files, algorithm = stego.parse_payload(payload, password)
                except ImageSteganographyException as e:
                    logger.error(f"❌ Image Decoding failed: {e}")
                    return 1

            else:
                if not hasattr(stego, "decode"):
                    raise ImageSteganographyException(
                        f"Algorithm {algorithm.name} does not support decoding"
                    )
                if not isinstance(stego, LSBStego):
                    raise ImageSteganographyException("Expected LSBStego instance")
                logger.info("Reading payload header (8 bytes)")
                try:
                    header_data = stego.decode(stego_path, 8)
                    logger.debug(f"Header data: {header_data.hex()}")
                except ImageSteganographyException as e:
                    logger.error(f"❌ Failed to read header from corrupted image: {e}")
                    return 1

                if header_data[:4] != self.MAGIC:
                    logger.debug("No hidden data found in image")
                    print("   ✗ No hidden data found")
                    print("\n✅ Decoding Complete!\n")
                    return 0
                else:
                    logger.info("Hidden data found in file")
                    print("    Hidden Data Found!")
                    print(f"   • Algorithm detected: {algorithm.name}")
                algorithm = Algorithm(header_data[5])
                encrypted = header_data[6]

                if encrypted:
                    payload_offset = 7 + self.SALT_SIZE + self.NONCE_SIZE
                else:
                    payload_offset = 7

                length_data = stego.decode(stego_path, payload_offset + 4)
                data_length = struct.unpack(
                    ">I", length_data[payload_offset : payload_offset + 4]
                )[0]

                total_length = payload_offset + 4 + data_length
                full_payload = stego.decode(stego_path, total_length)
                try:
                    extracted_files, _ = self.parse_payload(full_payload, password)
                except ImageSteganographyException as e:
                    logger.error(f"❌ Image Decoding failed: {e}")
                    return 1

            print("   Hidden Files:")
            for file_info in extracted_files:
                print(f"   • {file_info.file_name} ({file_info.file_size_mb})")
                output_path = os.path.join(output_dir, file_info.full_path)
                output_file_dir = os.path.dirname(output_path)
                if output_file_dir:
                    os.makedirs(output_file_dir, exist_ok=True)
                    logger.debug(f"Created directory: {output_file_dir}")
                print("\n🔄 Extracting Hidden Files...")
                print(f"   • Output Directory: '{os.path.dirname(output_path)}'")

                file_data = file_info.file_data
                if file_data is None:
                    raise ImageSteganographyException(
                        f"No data found for file {file_info.file_name}"
                    )

                with open(output_path, "wb") as f:
                    f.write(file_data)

                logger.info(
                    f"Extracted: {file_info.file_name} ({file_info.file_size} bytes) -> {output_path}"
                )

            print("\n✅ Decoding Complete!\n")
            return 0

        except Exception as e:
            raise
        except OSError as e:
            logger.error(f"Error decoding image (corrupt/unreadable): {e}", exc_info=True)
            return 1
        except Exception as e:
            logger.error(f"Unexpected error decoding image: {e}", exc_info=True)
            return 1


class ImageGenerator:
    def __init__(self, out_dir, width=512, height=512, frames_per_gif=20):
        self.WIDTH = width
        self.HEIGHT = height
        self.FRAMES_PER_GIF = frames_per_gif
        os.makedirs(out_dir, exist_ok=True)
        self.OUT = out_dir
        self.RUN_SEED = int(time.time_ns())
        self.rng = np.random.default_rng(self.RUN_SEED)

        self.PALETTE_IMG = Image.new("P", (1, 1))
        self.PALETTE_IMG.putpalette(self.fixed_rgb_palette())

    def create_secret_files(self):
        try:
            logger.debug("Creating test_secret_small.txt")
            with open(f"{self.OUT}/test_secret_small.txt", "w") as f:
                f.write("YOLO")
            print("   ✓ Created test_secret_small.txt")
            logger.info("Created test_secret_small.txt")

            logger.debug("Creating test_secret.txt")
            with open(f"{self.OUT}/test_secret.txt", "w") as f:
                f.write(
                    "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExY3JqdDJ2Y3VhcHR0OXY1d2RkMGQxdmJmbXdobGI1bnp1dWx0a3NxMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Yxg7MDkPj4kmI/giphy.gif"
                )
            print("   ✓ Created test_secret.txt")
            logger.info("Created test_secret.txt")
        except Exception as e:
            logger.exception("Failed to create text files")
            print(f"❌ Error creating text files: {e}")
            return 1

    def strip_metadata(self, image: Image.Image) -> Image.Image:
        clean = Image.new(image.mode, image.size)
        clean.putdata(list(image.getdata()))
        return clean

    def fixed_rgb_palette(self):
        palette = []
        for r in range(0, 256, 51):
            for g in range(0, 256, 51):
                for b in range(0, 256, 51):
                    palette.extend([r, g, b])
        return palette[:768]

    def generate_pattern(self, design_type: str) -> np.ndarray:
        base = self.rng.integers(
            0, 256, size=(self.HEIGHT, self.WIDTH, 3), dtype=np.uint8
        )

        if design_type == "gradient":
            x = np.linspace(0, 255, self.WIDTH, dtype=np.uint8)
            y = np.linspace(0, 255, self.HEIGHT, dtype=np.uint8)
            base[..., 0] = np.tile(x, (self.HEIGHT, 1))
            base[..., 1] = np.tile(y[:, None], (1, self.WIDTH))
            base[..., 2] = np.flipud(np.tile(x, (self.HEIGHT, 1)))
            base = (base.astype(np.uint16) + self.rng.integers(0, 256, size=3)).astype(
                np.uint8
            )

        elif design_type == "channels":
            idx = self.rng.permutation(3)
            base = base[..., idx]

        elif design_type == "waves":
            xv, yv = np.meshgrid(
                np.linspace(0, 2 * np.pi, self.WIDTH),
                np.linspace(0, 2 * np.pi, self.HEIGHT),
            )
            base[..., 0] = (
                (np.sin(xv + self.rng.random() * 2 * np.pi) * 127 + 128) % 256
            ).astype(np.uint8)
            base[..., 1] = (
                (np.sin(yv + self.rng.random() * 2 * np.pi) * 127 + 128) % 256
            ).astype(np.uint8)
            base[..., 2] = (
                (np.sin(xv + yv + self.rng.random() * 2 * np.pi) * 127 + 128) % 256
            ).astype(np.uint8)

        return base

    def save_static_formats(self):
        design_type = self.rng.choice(["noise", "gradient", "channels", "waves"])
        rgb = self.generate_pattern(design_type)
        img = self.strip_metadata(Image.fromarray(rgb, "RGB"))

        img.save(os.path.join(self.OUT, "image.bmp"))
        print("   ✓ Created image.bmp")
        img.save(os.path.join(self.OUT, "image.png"), compress_level=9)
        print("   ✓ Created image.png")
        img.save(
            os.path.join(self.OUT, "image.jpg"),
            quality=95,
            subsampling=0,
            optimize=False,
            progressive=False,
        )
        print("   ✓ Created image.jpg")
        img.save(os.path.join(self.OUT, "image.tiff"), compression="raw")
        print("   ✓ Created image.tiff")
        img.save(
            os.path.join(self.OUT, "image.webp"),
            format="WEBP",
            lossless=True,
            quality=100,
            method=6,
        )
        print("   ✓ Created image.webp")

        gif_static = img.quantize(palette=self.PALETTE_IMG, dither=Image.Dither.NONE)
        gif_static.save(os.path.join(self.OUT, "image_static.gif"), optimize=False)
        print("   ✓ Created image_static.gif")

    def save_animated_gif(self):
        frames = []
        designs = ["noise", "gradient", "channels", "waves"]
        for _ in range(self.FRAMES_PER_GIF):
            design_type = self.rng.choice(designs)
            frame_rgb = self.generate_pattern(design_type)
            frame = self.strip_metadata(Image.fromarray(frame_rgb, "RGB"))
            frame = frame.quantize(palette=self.PALETTE_IMG, dither=Image.Dither.FLOYDSTEINBERG)
            frames.append(frame)

        frames[0].save(
            os.path.join(self.OUT, "image_animated.gif"),
            save_all=True,
            append_images=frames[1:],
            duration=80,
            loop=0,
            optimize=False,
        )
        print("   ✓ Created image_animated.gif")

    def save_svg(self):
        dwg = svgwrite.Drawing(
            os.path.join(self.OUT, "image.svg"),
            size=(self.WIDTH, self.HEIGHT),
            profile="full",
        )

        c1 = self.rng.integers(0, 256, size=3)
        c2 = self.rng.integers(0, 256, size=3)
        c3 = self.rng.integers(0, 256, size=3)

        gradient = dwg.linearGradient(start=(0, 0), end=(1, 1), id="rgbGradient")
        gradient.add_stop_color(0.0, f"rgb({c1[0]},{c1[1]},{c1[2]})")
        gradient.add_stop_color(0.5, f"rgb({c2[0]},{c2[1]},{c2[2]})")
        gradient.add_stop_color(1.0, f"rgb({c3[0]},{c3[1]},{c3[2]})")
        dwg.defs.add(gradient)
        dwg.add(
            dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="url(#rgbGradient)")
        )
        dwg.save()
        print("   ✓ Created image.svg")

    def generate_all(self):
        self.create_secret_files()
        self.save_static_formats()
        self.save_animated_gif()
        self.save_svg()
        print("\n✅ Image Creation Complete!")
