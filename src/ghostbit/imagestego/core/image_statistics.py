#!/usr/bin/env python3
import os
import math
import logging
import numpy as np
from PIL import Image
from typing import List, Dict, Union, Any
from collections import Counter
import xml.etree.ElementTree as ET

logger = logging.getLogger("ghostbit.imagestego.statistics")


class ImageStatisticsException(Exception):
    """Base exception for image statistics operations"""

    pass


class StatisticalAnalysis:
    """Statistical analysis tools for image steganography"""

    @staticmethod
    def shannon_entropy_pixels(data: Any) -> float:
        """Calculate Shannon entropy for pixel data"""
        try:
            logger.debug("Calculating shannon_entropy_pixels")

            counts = Counter(data)
            total = sum(counts.values())

            if total == 0:
                logger.warning("Empty data provided to shannon_entropy_pixels")
                return 0.0

            entropy = 0.0
            for c in counts.values():
                p = c / total
                entropy -= p * math.log2(p)

            logger.debug(f"Shannon entropy (pixels): {entropy:.4f}")
            return entropy

        except Exception as e:
            logger.error(f"Error calculating shannon_entropy_pixels: {e}")
            raise ImageStatisticsException(f"Failed to calculate pixel entropy: {e}")

    @staticmethod
    def shannon_entropy_bytes(data: bytes) -> float:
        """Calculate Shannon entropy for byte data"""
        try:
            logger.debug("Calculating shannon_entropy_bytes")

            if not data:
                logger.warning("Empty data provided to shannon_entropy_bytes")
                return 0.0

            counts = Counter(data)
            total = len(data)
            entropy = -sum(
                (count / total) * math.log2(count / total) for count in counts.values()
            )

            logger.debug(f"Shannon entropy (bytes): {entropy:.4f}")
            return entropy

        except Exception as e:
            logger.error(f"Error calculating shannon_entropy_bytes: {e}")
            raise ImageStatisticsException(f"Failed to calculate byte entropy: {e}")

    @staticmethod
    def shannon_entropy_bytes_delta(origin_path: str, stego_path: str) -> float:
        """Calculate difference in Shannon entropy between original and stego files"""
        try:
            logger.info(f"Calculating entropy delta: {origin_path} vs {stego_path}")

            if not os.path.exists(origin_path):
                raise FileNotFoundError(f"Origin file not found: {origin_path}")
            if not os.path.exists(stego_path):
                raise FileNotFoundError(f"Stego file not found: {stego_path}")

            with open(origin_path, "rb") as f:
                origin_data = f.read()
                if not origin_data:
                    logger.warning(f"Empty origin file: {origin_path}")
                    origin_entropy = 0.0
                else:
                    origin_entropy = StatisticalAnalysis.shannon_entropy_bytes(
                        origin_data
                    )

            with open(stego_path, "rb") as f:
                stego_data = f.read()
                if not stego_data:
                    logger.warning(f"Empty stego file: {stego_path}")
                    stego_entropy = 0.0
                else:
                    stego_entropy = StatisticalAnalysis.shannon_entropy_bytes(
                        stego_data
                    )

            delta = stego_entropy - origin_entropy
            logger.info(
                f"Entropy delta: {delta:.6f} (origin={origin_entropy:.4f}, stego={stego_entropy:.4f})"
            )
            return delta

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error calculating entropy delta: {e}")
            raise ImageStatisticsException(f"Failed to calculate entropy delta: {e}")

    @staticmethod
    def lsb_chi_square(image: Image.Image) -> Dict[str, float]:
        """
        Chi-square test for LSB steganography detection.
        Lower values indicate less detectable steganography.
        """
        try:
            logger.debug("Initiating lsb_chi_square analysis")

            img_array = np.array(image.convert("RGB"))
            logger.debug(f"Image array shape: {img_array.shape}")

            results: Dict[str, float] = {}
            for channel_idx, channel_name in enumerate(["R", "G", "B"]):
                channel = img_array[:, :, channel_idx].flatten()

                pairs = []
                for i in range(0, 256, 2):
                    count_even = np.sum(channel == i)
                    count_odd = np.sum(channel == i + 1)
                    if count_even + count_odd > 0:
                        pairs.append((count_even, count_odd))

                chi_stat: float = 0.0
                for even, odd in pairs:
                    expected = (even + odd) / 2
                    if expected > 0:
                        chi_stat += (
                            (even - expected) ** 2 + (odd - expected) ** 2
                        ) / expected

                results[channel_name] = float(chi_stat)
                logger.debug(f"Chi-square {channel_name}: {chi_stat:.4f}")

            results["average"] = float(np.mean(list(results.values())))
            results["median"] = float(np.median(list(results.values())))

            logger.info(f"LSB chi-square complete: avg={results['average']:.4f}")
            return results

        except Exception as e:
            logger.error(f"Error in lsb_chi_square: {e}")
            raise ImageStatisticsException(f"Failed to calculate LSB chi-square: {e}")

    @staticmethod
    def palette_chi_square(frame: Image.Image) -> float:
        """Calculate chi-square for palette data"""
        try:
            logger.debug("Calculating palette_chi_square")

            palette = frame.getpalette()
            if not palette:
                logger.warning("No palette found in frame")
                return 0.0

            chi = 0.0
            for channel in range(3):
                values = palette[channel::3]
                for i in range(0, 256, 2):
                    even = values.count(i)
                    odd = values.count(i + 1)
                    if even + odd > 0:
                        exp = (even + odd) / 2
                        chi += ((even - exp) ** 2 + (odd - exp) ** 2) / exp

            logger.debug(f"Palette chi-square: {chi:.4f}")
            return float(chi)

        except Exception as e:
            logger.error(f"Error calculating palette_chi_square: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate palette chi-square: {e}"
            )

    @staticmethod
    def pixel_chi_square(frame: Image.Image) -> float:
        """Calculate chi-square for pixel data"""
        try:
            logger.debug("Calculating pixel_chi_square")

            pixels = np.array(frame.getdata(), dtype=np.uint8).flatten()
            logger.debug(f"Analyzing {len(pixels)} pixels")

            pairs = []
            for i in range(0, 256, 2):
                count_even = np.sum(pixels == i)
                count_odd = np.sum(pixels == i + 1)
                if count_even + count_odd > 0:
                    pairs.append((count_even, count_odd))

            chi = 0.0
            for even, odd in pairs:
                expected = (even + odd) / 2
                if expected > 0:
                    chi += ((even - expected) ** 2 + (odd - expected) ** 2) / expected

            logger.debug(f"Pixel chi-square: {chi:.4f}")
            return float(chi)

        except Exception as e:
            logger.error(f"Error calculating pixel_chi_square: {e}")
            raise ImageStatisticsException(f"Failed to calculate pixel chi-square: {e}")

    @staticmethod
    def lsb_chi_square_delta(cover_path: str, stego_path: str) -> Dict[str, Any]:
        """
        Calculate chi-square delta between cover and stego images.
        """
        try:
            logger.info(
                f"Calculating LSB chi-square delta: {cover_path} vs {stego_path}"
            )

            if not os.path.exists(cover_path):
                raise FileNotFoundError(f"Cover image not found: {cover_path}")
            if not os.path.exists(stego_path):
                raise FileNotFoundError(f"Stego image not found: {stego_path}")

            with (
                Image.open(cover_path) as cover_img,
                Image.open(stego_path) as stego_img,
            ):
                cover_stats = StatisticalAnalysis.lsb_chi_square(cover_img)
                stego_stats = StatisticalAnalysis.lsb_chi_square(stego_img)

            delta_stats = {
                k: stego_stats[k] - cover_stats[k] for k in cover_stats.keys()
            }

            results: Dict[str, Any] = {"cover": cover_stats, "stego": stego_stats, "delta": delta_stats}

            logger.info(
                f"LSB chi-square delta complete: avg_delta={delta_stats['average']:.4f}"
            )
            return results

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error calculating lsb_chi_square_delta: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate LSB chi-square delta: {e}"
            )

    @staticmethod
    def gif_palette_entropy(gif_path: str) -> List[float]:
        """Calculate palette entropy for each frame in a GIF"""
        try:
            logger.info(f"Calculating GIF palette entropy: {gif_path}")

            if not os.path.exists(gif_path):
                raise FileNotFoundError(f"GIF file not found: {gif_path}")

            entropies: List[float] = []
            with Image.open(gif_path) as gif:
                n_frames = getattr(gif, "n_frames", 1)
                logger.debug(f"Processing {n_frames} frames")

                for i in range(n_frames):
                    gif.seek(i)
                    if gif.mode != "P":
                        logger.debug(f"Frame {i} not in palette mode, skipping")
                        continue

                    palette = gif.getpalette()
                    if not palette:
                        logger.debug(f"Frame {i} has no palette, skipping")
                        continue

                    entropy = StatisticalAnalysis.shannon_entropy_pixels(palette)
                    entropies.append(entropy)
                    logger.debug(f"Frame {i} palette entropy: {entropy:.4f}")

            logger.info(f"Calculated entropy for {len(entropies)} frames")
            return entropies

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error calculating gif_palette_entropy: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate GIF palette entropy: {e}"
            )

    @staticmethod
    def gif_entropy_delta(
        cover_path: str, stego_path: str
    ) -> Dict[str, Union[List[float], float]]:
        """
        Compute entropy delta per frame between cover and stego GIFs.
        """
        try:
            logger.info(f"Calculating GIF entropy delta: {cover_path} vs {stego_path}")

            cover_entropies = StatisticalAnalysis.gif_palette_entropy(cover_path)
            stego_entropies = StatisticalAnalysis.gif_palette_entropy(stego_path)

            n = min(len(cover_entropies), len(stego_entropies))

            if n == 0:
                logger.warning("No frames with palettes found in one or both GIFs")
                return {
                    "per_frame": [],
                    "average": 0.0,
                    "median": 0.0,
                    "max_abs": 0.0,
                }

            deltas = [stego_entropies[i] - cover_entropies[i] for i in range(n)]

            results: Dict[str, Union[List[float], float]] = {
                "per_frame": deltas,
                "average": float(np.mean(deltas)),
                "median": float(np.median(deltas)),
                "max_abs": float(np.max(np.abs(deltas))),
            }

            logger.info(
                f"GIF entropy delta: avg={results['average']:.6f}, max_abs={results['max_abs']:.6f}"
            )
            return results

        except Exception as e:
            logger.error(f"Error calculating gif_entropy_delta: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate GIF entropy delta: {e}"
            )

    @staticmethod
    def gif_chi_square_delta(cover_path: str, stego_path: str) -> Dict[str, Union[List[float], float]]:
        """
        Compute frame-by-frame chi-square delta for GIFs (palette & pixel).
        """
        try:
            logger.info(
                f"Calculating GIF chi-square delta: {cover_path} vs {stego_path}"
            )

            cover_stats = StatisticalAnalysis.gif_chi_square(cover_path)
            stego_stats = StatisticalAnalysis.gif_chi_square(stego_path)

            # Extract and type-narrow the values
            cover_pixel_raw = cover_stats["frames_pixel"]
            stego_pixel_raw = stego_stats["frames_pixel"]
            cover_palette_raw = cover_stats["frames_palette"]
            stego_palette_raw = stego_stats["frames_palette"]
            
            # Type narrowing: ensure we have lists
            if not isinstance(cover_pixel_raw, list) or not isinstance(stego_pixel_raw, list):
                raise ImageStatisticsException("Invalid chi-square results: frames_pixel must be a list")
            
            if not isinstance(cover_palette_raw, list) or not isinstance(stego_palette_raw, list):
                raise ImageStatisticsException("Invalid chi-square results: frames_palette must be a list")
            
            cover_pixel: List[float] = cover_pixel_raw
            stego_pixel: List[float] = stego_pixel_raw
            cover_palette: List[float] = cover_palette_raw
            stego_palette: List[float] = stego_palette_raw

            n_frames = min(len(cover_pixel), len(stego_pixel))

            if n_frames == 0:
                logger.warning("No frames to compare")
                return {
                    "delta_pixel_per_frame": [],
                    "delta_pixel_average": 0.0,
                    "delta_pixel_median": 0.0,
                    "delta_pixel_max_abs": 0.0,
                    "delta_palette_per_frame": [],
                    "delta_palette_average": 0.0,
                    "delta_palette_median": 0.0,
                    "delta_palette_max_abs": 0.0,
                }

            delta_pixel = [
                stego_pixel[i] - cover_pixel[i]
                for i in range(n_frames)
            ]

            delta_palette = [
                stego_palette[i] - cover_palette[i]
                for i in range(min(len(cover_palette), len(stego_palette)))
            ]

            results: Dict[str, Union[List[float], float]] = {
                "delta_pixel_per_frame": delta_pixel,
                "delta_pixel_average": float(np.mean(delta_pixel)),
                "delta_pixel_median": float(np.median(delta_pixel)),
                "delta_pixel_max_abs": float(np.max(np.abs(delta_pixel))),
                "delta_palette_per_frame": delta_palette,
                "delta_palette_average": (
                    float(np.mean(delta_palette)) if delta_palette else 0.0
                ),
                "delta_palette_median": (
                    float(np.median(delta_palette)) if delta_palette else 0.0
                ),
                "delta_palette_max_abs": (
                    float(np.max(np.abs(delta_palette))) if delta_palette else 0.0
                ),
            }

            logger.info(
                f"GIF chi-square delta complete: pixel_avg={results['delta_pixel_average']:.4f}"
            )
            return results

        except Exception as e:
            logger.error(f"Error calculating gif_chi_square_delta: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate GIF chi-square delta: {e}"
            )
    # @staticmethod
    # def gif_chi_square_delta(cover_path: str, stego_path: str) -> Dict[str, Union[List[float], float]]:
    #     """
    #     Compute frame-by-frame chi-square delta for GIFs (palette & pixel).
    #     """
    #     try:
    #         logger.info(
    #             f"Calculating GIF chi-square delta: {cover_path} vs {stego_path}"
    #         )

    #         cover_stats = StatisticalAnalysis.gif_chi_square(cover_path)
    #         stego_stats = StatisticalAnalysis.gif_chi_square(stego_path)

    #         cover_pixel = cover_stats["frames_pixel"]
    #         stego_pixel = stego_stats["frames_pixel"]
    #         cover_palette = cover_stats["frames_palette"]
    #         stego_palette = stego_stats["frames_palette"]

    #         n_frames = min(len(cover_pixel), len(stego_pixel))

    #         if n_frames == 0:
    #             logger.warning("No frames to compare")
    #             return {
    #                 "delta_pixel_per_frame": [],
    #                 "delta_pixel_average": 0.0,
    #                 "delta_pixel_median": 0.0,
    #                 "delta_pixel_max_abs": 0.0,
    #                 "delta_palette_per_frame": [],
    #                 "delta_palette_average": 0.0,
    #                 "delta_palette_median": 0.0,
    #                 "delta_palette_max_abs": 0.0,
    #             }

    #         delta_pixel = [
    #             stego_pixel[i] - cover_pixel[i]
    #             for i in range(n_frames)
    #         ]

    #         delta_palette = [
    #             stego_palette[i] - cover_palette[i]
    #             for i in range(min(len(cover_palette), len(stego_palette)))
    #         ]

    #         results: Dict[str, Union[List[float], float]] = {
    #             "delta_pixel_per_frame": delta_pixel,
    #             "delta_pixel_average": float(np.mean(delta_pixel)),
    #             "delta_pixel_median": float(np.median(delta_pixel)),
    #             "delta_pixel_max_abs": float(np.max(np.abs(delta_pixel))),
    #             "delta_palette_per_frame": delta_palette,
    #             "delta_palette_average": (
    #                 float(np.mean(delta_palette)) if delta_palette else 0.0
    #             ),
    #             "delta_palette_median": (
    #                 float(np.median(delta_palette)) if delta_palette else 0.0
    #             ),
    #             "delta_palette_max_abs": (
    #                 float(np.max(np.abs(delta_palette))) if delta_palette else 0.0
    #             ),
    #         }

    #         logger.info(
    #             f"GIF chi-square delta complete: pixel_avg={results['delta_pixel_average']:.4f}"
    #         )
    #         return results

    #     except Exception as e:
    #         logger.error(f"Error calculating gif_chi_square_delta: {e}")
    #         raise ImageStatisticsException(
    #             f"Failed to calculate GIF chi-square delta: {e}"
    #         )

    @staticmethod
    def gif_chi_square(gif_path: str) -> Dict[str, Union[List[float], float]]:
        """
        Chi-square analysis for GIFs (per frame and average)
        """
        try:
            logger.info(f"Calculating GIF chi-square: {gif_path}")

            if not os.path.exists(gif_path):
                raise FileNotFoundError(f"GIF file not found: {gif_path}")

            with Image.open(gif_path) as gif:
                n_frames = getattr(gif, "n_frames", 1)
                logger.debug(f"Processing {n_frames} frames")

                chi_palette_values: List[float] = []
                chi_pixel_values: List[float] = []

                for frame_idx in range(n_frames):
                    try:
                        gif.seek(frame_idx)

                        if gif.mode != "P":
                            frame = gif.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
                        else:
                            frame = gif.copy()

                        chi_palette_stat = StatisticalAnalysis.palette_chi_square(frame)
                        chi_palette_values.append(float(chi_palette_stat))

                        chi_pixel_stat = StatisticalAnalysis.pixel_chi_square(frame)
                        chi_pixel_values.append(float(chi_pixel_stat))

                        logger.debug(
                            f"Frame {frame_idx}: palette_chi={chi_palette_stat:.4f}, pixel_chi={chi_pixel_stat:.4f}"
                        )

                    except Exception as e:
                        logger.warning(f"Error processing frame {frame_idx}: {e}")
                        continue

                if not chi_pixel_values:
                    logger.warning("No frames successfully processed")
                    return {
                        "frames_palette": [],
                        "average_palette": 0.0,
                        "median_palette": 0.0,
                        "frames_pixel": [],
                        "average_pixel": 0.0,
                        "median_pixel": 0.0,
                    }

                results: Dict[str, Union[List[float], float]] = {
                    "frames_palette": chi_palette_values,
                    "average_palette": (
                        float(np.mean(chi_palette_values))
                        if chi_palette_values
                        else 0.0
                    ),
                    "median_palette": (
                        float(np.median(chi_palette_values))
                        if chi_palette_values
                        else 0.0
                    ),
                    "frames_pixel": chi_pixel_values,
                    "average_pixel": float(np.mean(chi_pixel_values)),
                    "median_pixel": float(np.median(chi_pixel_values)),
                }

                logger.info(
                    f"GIF chi-square complete: {n_frames} frames, avg_pixel={results['average_pixel']:.4f}"
                )
                return results

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error calculating gif_chi_square: {e}")
            raise ImageStatisticsException(f"Failed to calculate GIF chi-square: {e}")

    @staticmethod
    def gif_calculate_mse(original_path: str, stego_path: str) -> Dict[str, Union[float, List[float]]]:
        """
        Calculate MSE (Mean Squared Error) per frame and average for a GIF.
        """
        try:
            logger.info(f"Calculating GIF MSE: {original_path} vs {stego_path}")

            if not os.path.exists(original_path):
                raise FileNotFoundError(f"Original GIF not found: {original_path}")
            if not os.path.exists(stego_path):
                raise FileNotFoundError(f"Stego GIF not found: {stego_path}")

            with (
                Image.open(original_path) as orig_gif,
                Image.open(stego_path) as stego_gif,
            ):
                n_frames = max(
                    getattr(orig_gif, "n_frames", 1), getattr(stego_gif, "n_frames", 1)
                )

                logger.debug(f"Processing {n_frames} frames")

                mse_list: List[float] = []

                for idx in range(n_frames):
                    try:
                        orig_gif.seek(idx % getattr(orig_gif, "n_frames", 1))
                        stego_gif.seek(idx % getattr(stego_gif, "n_frames", 1))

                        orig_frame = np.array(orig_gif.convert("RGB"), dtype=np.float32)
                        stego_frame = np.array(
                            stego_gif.convert("RGB"), dtype=np.float32
                        )

                        mse = float(np.mean((orig_frame - stego_frame) ** 2))
                        mse_list.append(mse)
                        logger.debug(f"Frame {idx} MSE: {mse:.6f}")

                    except Exception as e:
                        logger.warning(f"Error processing frame {idx}: {e}")
                        continue

                if not mse_list:
                    logger.warning("No frames successfully processed")
                    return {"mse_per_frame": [], "mse_average": 0.0}

                results: Dict[str, Union[float, List[float]]] = {
                    "mse_per_frame": mse_list,
                    "mse_average": float(np.mean(mse_list)),
                }

                logger.info(f"GIF MSE complete: avg={results['mse_average']:.6f}")
                return results

        except FileNotFoundError:
            raise ImageStatisticsException('File not found')
        except Exception as e:
            logger.error(f"Error calculating gif_calculate_mse: {e}")
            raise ImageStatisticsException(f"Failed to calculate GIF MSE: {e}")

    @staticmethod
    def gif_calculate_psnr(original_path: str, stego_path: str) -> Dict[str, Union[str, float, List[float]]]:
        """
        Calculate PSNR (Peak Signal-to-Noise Ratio) per frame and average for a GIF.
        """
        try:
            logger.info(f"Calculating GIF PSNR: {original_path} vs {stego_path}")

            mse_results = StatisticalAnalysis.gif_calculate_mse(
                original_path, stego_path
            )
            mse_per_frame = mse_results["mse_per_frame"]
            
            if not isinstance(mse_per_frame, list):
                raise ImageStatisticsException("Invalid MSE results")
            
            psnr_list: List[float] = []

            for idx, mse in enumerate(mse_per_frame):
                if mse == 0:
                    psnr = float("inf")
                    logger.debug(f"Frame {idx} PSNR: inf (identical frames)")
                else:
                    psnr = 10 * np.log10((255**2) / mse)
                    logger.debug(f"Frame {idx} PSNR: {psnr:.2f} dB")
                psnr_list.append(psnr)

            finite_psnrs = [p for p in psnr_list if p != float("inf")]

            results: Dict[str, Union[str, float, List[float]]] = {
                "psnr_per_frame": psnr_list,
                "psnr_average": (
                    float(np.mean(finite_psnrs)) if finite_psnrs else float("inf")
                ),
            }

            logger.info(f"GIF PSNR complete: avg={results['psnr_average']:.2f} dB")
            return results

        except Exception as e:
            logger.error(f"Error calculating gif_calculate_psnr: {e}")
            raise ImageStatisticsException(f"Failed to calculate GIF PSNR: {e}")

    @staticmethod
    def lsb_calculate_psnr(cover_path: str, stego: Image.Image) -> float:
        """Calculate Peak Signal-to-Noise Ratio (higher is better, >40dB is excellent)"""
        try:
            logger.debug(f"Calculating LSB PSNR for {cover_path}")
            assert stego is not None
            if not os.path.exists(cover_path):
                raise FileNotFoundError(f"Cover image not found: {cover_path}")

            original = Image.open(cover_path)
            orig_array = np.array(original.convert("RGB")).astype(float)
            stego_array = np.array(stego.convert("RGB")).astype(float)

            if orig_array.shape != stego_array.shape:
                raise ImageStatisticsException(
                    f"Image dimension mismatch: {orig_array.shape} vs {stego_array.shape}"
                )

            mse = np.mean((orig_array - stego_array) ** 2)
            if mse == 0:
                logger.debug("PSNR: inf (identical images)")
                return float("inf")

            max_pixel = 255.0
            psnr = 10 * math.log10((max_pixel**2) / mse)

            logger.debug(f"PSNR: {psnr:.2f} dB")
            return float(psnr)

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error calculating lsb_calculate_psnr: {e}")
            raise ImageStatisticsException(f"Failed to calculate LSB PSNR: {e}")

    @staticmethod
    def lsb_calculate_mse(cover_path: str, stego: Image.Image) -> float:
        """Calculate Mean Squared Error (lower is better)"""
        try:
            logger.debug(f"Calculating LSB MSE for {cover_path}")
            assert stego is not None
            if not os.path.exists(cover_path):
                raise FileNotFoundError(f"Cover image not found: {cover_path}")

            original = Image.open(cover_path)
            orig_array = np.array(original.convert("RGB")).astype(float)
            stego_array = np.array(stego.convert("RGB")).astype(float)

            if orig_array.shape != stego_array.shape:
                raise ImageStatisticsException(
                    f"Image dimension mismatch: {orig_array.shape} vs {stego_array.shape}"
                )

            mse = float(np.mean((orig_array - stego_array) ** 2))
            logger.debug(f"MSE: {mse:.6f}")
            return mse

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error calculating lsb_calculate_mse: {e}")
            raise ImageStatisticsException(f"Failed to calculate LSB MSE: {e}")

    @staticmethod
    def lsb_calculate_histogram_difference(
        cover_path: str, stego: Image.Image
    ) -> Dict[str, float]:
        """Calculate histogram differences between original and stego images"""
        try:
            logger.debug(f"Calculating histogram difference for {cover_path}")
            assert stego is not None
            if not os.path.exists(cover_path):
                raise FileNotFoundError(f"Cover image not found: {cover_path}")

            original = Image.open(cover_path)
            orig_array = np.array(original.convert("RGB"))
            stego_array = np.array(stego.convert("RGB"))

            if orig_array.shape != stego_array.shape:
                raise ImageStatisticsException(
                    f"Image dimension mismatch: {orig_array.shape} vs {stego_array.shape}"
                )

            results: Dict[str, float] = {}
            for channel_idx, channel_name in enumerate(["R", "G", "B"]):
                orig_hist, _ = np.histogram(
                    orig_array[:, :, channel_idx], bins=256, range=(0, 256)
                )
                stego_hist, _ = np.histogram(
                    stego_array[:, :, channel_idx], bins=256, range=(0, 256)
                )

                diff = np.abs(orig_hist.astype(float) - stego_hist.astype(float))
                results[channel_name] = float(
                    np.sum(diff) / orig_array.shape[0] / orig_array.shape[1]
                )
                logger.debug(
                    f"Histogram diff {channel_name}: {results[channel_name]:.6f}"
                )

            results["average"] = float(np.mean(list(results.values())))
            logger.debug(f"Average histogram difference: {results['average']:.6f}")

            return results

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error calculating histogram difference: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate histogram difference: {e}"
            )

    @staticmethod
    def svg_calculate_element_patterns(file_path: str) -> Dict[str, int]:
        """Calculate suspicious patterns in SVG elements"""
        try:
            logger.debug(f"Calculating SVG element patterns: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"SVG file not found: {file_path}")

            tree = ET.parse(file_path)
            root = tree.getroot()

            comment_count = 0
            long_ids = 0
            long_classes = 0

            for elem in root.iter():
                id_val = elem.attrib.get("id", "")
                class_val = elem.attrib.get("class", "")
                if len(id_val) > 20:
                    long_ids += 1
                if len(class_val) > 20:
                    long_classes += 1

            try:
                for event, elem in ET.iterparse(file_path, events=("comment",)):
                    comment_count += 1
            except Exception as e:
                logger.warning(f"Error parsing comments: {e}")

            suspicious_patterns: Dict[str, int] = {
                "comments": comment_count,
                "long_ids": long_ids,
                "long_classes": long_classes,
            }

            logger.debug(f"SVG patterns: {suspicious_patterns}")
            return suspicious_patterns

        except FileNotFoundError:
            raise
        except ET.ParseError as e:
            logger.error(f"XML parse error in {file_path}: {e}")
            raise ImageStatisticsException(f"Failed to parse SVG file: {e}")
        except Exception as e:
            logger.error(f"Error calculating SVG element patterns: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate SVG element patterns: {e}"
            )

    @staticmethod
    def svg_calculate_pattern_delta(origin_path: str, stego_path: str) -> Dict[str, int]:
        """Calculate delta in SVG element patterns"""
        try:
            logger.info(f"Calculating SVG pattern delta: {origin_path} vs {stego_path}")

            origin_patterns = StatisticalAnalysis.svg_calculate_element_patterns(
                origin_path
            )
            stego_patterns = StatisticalAnalysis.svg_calculate_element_patterns(
                stego_path
            )

            delta: Dict[str, int] = {}
            for key in origin_patterns:
                delta[key] = stego_patterns.get(key, 0) - origin_patterns.get(key, 0)

            logger.info(f"SVG pattern delta: {delta}")
            return delta

        except Exception as e:
            logger.error(f"Error calculating SVG pattern delta: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate SVG pattern delta: {e}"
            )

    @staticmethod
    def svg_calculate_elements(file_path: str) -> Dict[str, int]:
        """Count SVG elements by type"""
        try:
            logger.debug(f"Calculating SVG elements: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"SVG file not found: {file_path}")

            tree = ET.parse(file_path)
            root = tree.getroot()

            element_counts: Counter[str] = Counter()
            for elem in root.iter():
                element_counts[elem.tag] += 1

            elements: Dict[str, int] = dict(element_counts)
            logger.debug(
                f"Found {len(elements)} unique element types, {sum(elements.values())} total elements"
            )
            return elements

        except FileNotFoundError:
            raise
        except ET.ParseError as e:
            logger.error(f"XML parse error in {file_path}: {e}")
            raise ImageStatisticsException(f"Failed to parse SVG file: {e}")
        except Exception as e:
            logger.error(f"Error calculating SVG elements: {e}")
            raise ImageStatisticsException(f"Failed to calculate SVG elements: {e}")

    @staticmethod
    def svg_calculate_numeric_stats(file_path: str) -> Dict[str, Union[int, float, None]]:
        """Calculate statistics on numeric values in SVG attributes"""
        try:
            logger.debug(f"Calculating SVG numeric stats: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"SVG file not found: {file_path}")

            tree = ET.parse(file_path)
            root = tree.getroot()

            numeric_values: List[float] = []
            for elem in root.iter():
                for attr, val in elem.attrib.items():
                    try:
                        numeric_values.extend(
                            [float(x) for x in val.replace(",", " ").split()]
                        )
                    except ValueError:
                        continue

            mean_val: Union[float, None]
            variance: Union[float, None]
            min_val: Union[float, None]
            max_val: Union[float, None]
            
            if numeric_values:
                mean_val = sum(numeric_values) / len(numeric_values)
                variance = sum((x - mean_val) ** 2 for x in numeric_values) / len(
                    numeric_values
                )
                min_val = min(numeric_values)
                max_val = max(numeric_values)
            else:
                mean_val = variance = min_val = max_val = None
                logger.debug("No numeric values found in SVG")

            numeric_stats: Dict[str, Union[int, float, None]] = {
                "count": len(numeric_values),
                "mean": mean_val,
                "variance": variance,
                "min": min_val,
                "max": max_val,
            }

            logger.debug(
                f"SVG numeric stats: count={numeric_stats['count']}, mean={mean_val}"
            )
            return numeric_stats

        except FileNotFoundError:
            raise
        except ET.ParseError as e:
            logger.error(f"XML parse error in {file_path}: {e}")
            raise ImageStatisticsException(f"Failed to parse SVG file: {e}")
        except Exception as e:
            logger.error(f"Error calculating SVG numeric stats: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate SVG numeric stats: {e}"
            )

    @staticmethod
    def svg_calculate_numeric_stats_delta(origin_path: str, stego_path: str) -> Dict[str, Union[int, float, None]]:
        """Calculate SVG numeric stats delta"""
        try:
            logger.info(
                f"Calculating SVG numeric stats delta: {origin_path} vs {stego_path}"
            )

            origin_stats = StatisticalAnalysis.svg_calculate_numeric_stats(origin_path)
            stego_stats = StatisticalAnalysis.svg_calculate_numeric_stats(stego_path)

            delta: Dict[str, Union[int, float, None]] = {}
            for key, origin_val in origin_stats.items():
                stego_val = stego_stats.get(key)

                if origin_val is None or stego_val is None:
                    delta[key] = None
                elif isinstance(origin_val, (int, float)) and isinstance(stego_val, (int, float)):
                    delta[key] = stego_val - origin_val
                else:
                    delta[key] = None

            logger.info("SVG numeric stats delta calculated")
            return delta

        except Exception as e:
            logger.error(f"Error calculating SVG numeric stats delta: {e}")
            raise ImageStatisticsException(
                f"Failed to calculate SVG numeric stats delta: {e}"
            )

    @staticmethod
    def analyze_lsb(file_path: str) -> Dict[str, float]:
        """Complete LSB image analysis"""
        try:
            logger.info(f"Analyzing LSB image: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Image file not found: {file_path}")

            with Image.open(file_path) as img:
                chi_stats = StatisticalAnalysis.lsb_chi_square(img)

            logger.info("LSB analysis complete")
            return chi_stats

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error analyzing LSB image: {e}")
            raise ImageStatisticsException(f"Failed to analyze LSB image: {e}")

    @staticmethod
    def analyze_gif(file_path: str) -> Dict[str, Any]:
        """Complete GIF analysis"""
        try:
            logger.info(f"Analyzing GIF: {file_path}")

            chi_sq = StatisticalAnalysis.gif_chi_square(file_path)
            palette_entropy = StatisticalAnalysis.gif_palette_entropy(file_path)

            results: Dict[str, Any] = {
                "chi_sq": chi_sq,
                "palette_entropy": palette_entropy,
            }

            logger.info("GIF analysis complete")
            return results

        except Exception as e:
            logger.error(f"Error analyzing GIF: {e}")
            raise ImageStatisticsException(f"Failed to analyze GIF: {e}")

    @staticmethod
    def compare_gifs(cover_path: str, stego_filepath: str) -> Dict[str, Any]:
        """Calculate GIF delta metrics"""
        try:
            logger.info(f"Comparing GIFs: {cover_path} vs {stego_filepath}")

            mse = StatisticalAnalysis.gif_calculate_mse(cover_path, stego_filepath)
            psnr = StatisticalAnalysis.gif_calculate_psnr(cover_path, stego_filepath)
            chi = StatisticalAnalysis.gif_chi_square_delta(cover_path, stego_filepath)
            entropy = StatisticalAnalysis.gif_entropy_delta(cover_path, stego_filepath)

            results: Dict[str, Any] = {
                "mse": mse,
                "psnr": psnr,
                "chi": chi,
                "entropy": entropy,
            }

            logger.info("GIF comparison complete")
            return results

        except Exception as e:
            logger.error(f"Error comparing GIFs: {e}")
            raise ImageStatisticsException(f"Failed to compare GIFs: {e}")

    @staticmethod
    def analyze_svg(file_path: str) -> Dict[str, Any]:
        """Complete SVG analysis"""
        try:
            logger.info(f"Analyzing SVG: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"SVG not found: {file_path}")

            with open(file_path, "rb") as f:
                raw_data = f.read()
                if raw_data:
                    entropy = StatisticalAnalysis.shannon_entropy_bytes(raw_data)
                else:
                    entropy = 0.0

            elements = StatisticalAnalysis.svg_calculate_elements(file_path)
            numeric_stats = StatisticalAnalysis.svg_calculate_numeric_stats(file_path)
            suspicious_patterns = StatisticalAnalysis.svg_calculate_element_patterns(
                file_path
            )

            results: Dict[str, Any] = {
                "entropy": entropy,
                "numeric_stats": numeric_stats,
                "element_counts": elements,
                "suspicious_patterns": suspicious_patterns,
            }

            logger.info("SVG analysis complete")
            return results

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error analyzing SVG: {e}")
            raise ImageStatisticsException(f"Failed to analyze SVG: {e}")

    @staticmethod
    def compare_svgs(original_path: str, stego_path: str) -> Dict[str, Any]:
        """Calculate SVG delta metrics"""
        try:
            logger.info(f"Comparing SVGs: {original_path} vs {stego_path}")

            entropy_delta = StatisticalAnalysis.shannon_entropy_bytes_delta(
                original_path, stego_path
            )
            suspicious_patterns_delta = StatisticalAnalysis.svg_calculate_pattern_delta(
                original_path, stego_path
            )
            numeric_stats_delta = StatisticalAnalysis.svg_calculate_numeric_stats_delta(
                original_path, stego_path
            )

            results: Dict[str, Any] = {
                "entropy_bytes_delta": entropy_delta,
                "suspicious_patterns_delta": suspicious_patterns_delta,
                "numeric_stats_delta": numeric_stats_delta,
            }

            logger.info("SVG comparison complete")
            return results

        except Exception as e:
            logger.error(f"Error comparing SVGs: {e}")
            raise ImageStatisticsException(f"Failed to compare SVGs: {e}")