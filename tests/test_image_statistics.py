#!/usr/bin/env python3
import os
import pytest
import numpy as np
from PIL import Image
import tempfile
import xml.etree.ElementTree as ET
from typing import List

from ghostbit.imagestego.core.image_statistics import (
    StatisticalAnalysis,
    ImageStatisticsException,
)


"""
Tests for imagestego.core.image_statistics module
"""


class TestStatisticalAnalysisBasic:
    """Test basic entropy and statistical functions"""

    def test_shannon_entropy_pixels_valid_data(self):
        """Test Shannon entropy calculation with valid pixel data"""
        data = [0, 1, 0, 1, 0, 1, 0, 1]
        entropy = StatisticalAnalysis.shannon_entropy_pixels(data)
        assert isinstance(entropy, float)
        assert 0.0 <= entropy <= 8.0

    def test_shannon_entropy_pixels_uniform(self):
        """Test entropy with uniform distribution (maximum entropy)"""
        data = list(range(256))
        entropy = StatisticalAnalysis.shannon_entropy_pixels(data)
        assert entropy == pytest.approx(8.0, rel=0.1)

    def test_shannon_entropy_pixels_constant(self):
        """Test entropy with constant data (zero entropy)"""
        data = [42] * 100
        entropy = StatisticalAnalysis.shannon_entropy_pixels(data)
        assert entropy == 0.0

    def test_shannon_entropy_pixels_empty(self):
        """Test entropy with empty data"""
        entropy = StatisticalAnalysis.shannon_entropy_pixels([])
        assert entropy == 0.0

    def test_shannon_entropy_bytes_valid(self):
        """Test byte entropy with valid data"""
        data = b"Hello, World!" * 10
        entropy = StatisticalAnalysis.shannon_entropy_bytes(data)
        assert isinstance(entropy, float)
        assert 0.0 <= entropy <= 8.0

    def test_shannon_entropy_bytes_empty(self):
        """Test byte entropy with empty data"""
        entropy = StatisticalAnalysis.shannon_entropy_bytes(b"")
        assert entropy == 0.0

    def test_shannon_entropy_bytes_random(self):
        """Test byte entropy with random data (should be high)"""
        np.random.seed(42)
        data = np.random.bytes(1000)
        entropy = StatisticalAnalysis.shannon_entropy_bytes(data)

        assert entropy > 6.0


class TestLSBChiSquare:
    """Test LSB chi-square analysis"""

    @pytest.fixture
    def rgb_image(self):
        """Create a test RGB image"""
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        return img

    @pytest.fixture
    def random_rgb_image(self):
        """Create a random RGB image"""
        np.random.seed(42)
        array = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        return Image.fromarray(array, mode="RGB")

    def test_lsb_chi_square_uniform_image(self, rgb_image):
        """Test chi-square on uniform color image"""
        result = StatisticalAnalysis.lsb_chi_square(rgb_image)
        assert isinstance(result, dict)
        assert "R" in result
        assert "G" in result
        assert "B" in result
        assert "average" in result
        assert "median" in result
        assert all(isinstance(v, float) for v in result.values())

    def test_lsb_chi_square_random_image(self, random_rgb_image):
        """Test chi-square on random image"""
        result = StatisticalAnalysis.lsb_chi_square(random_rgb_image)
        assert result["average"] > 0
        assert result["median"] > 0

    def test_lsb_chi_square_delta_with_files(self, tmp_path):
        """Test chi-square delta between two images"""

        img1 = Image.new("RGB", (50, 50), color=(100, 100, 100))
        img2 = Image.new("RGB", (50, 50), color=(101, 101, 101))
        
        path1 = tmp_path / "cover.png"
        path2 = tmp_path / "stego.png"
        
        img1.save(path1)
        img2.save(path2)
        
        result = StatisticalAnalysis.lsb_chi_square_delta(str(path1), str(path2))
        
        assert "cover" in result
        assert "stego" in result
        assert "delta" in result
        assert isinstance(result["delta"], dict)
        assert "average" in result["delta"]

    def test_lsb_chi_square_delta_missing_file(self, tmp_path):
        """Test chi-square delta with missing file"""
        path1 = tmp_path / "nonexistent.png"
        path2 = tmp_path / "also_nonexistent.png"
        
        with pytest.raises(FileNotFoundError):
            StatisticalAnalysis.lsb_chi_square_delta(str(path1), str(path2))


class TestGIFStatistics:
    """Test GIF-specific statistical analysis"""

    @pytest.fixture
    def static_gif(self, tmp_path):
        """Create a static GIF for testing"""
        img = Image.new("P", (50, 50), color=0)
        palette = list(range(256)) * 3
        img.putpalette(palette)
        path = tmp_path / "static.gif"
        img.save(path, format="GIF")
        return str(path)

    @pytest.fixture
    def animated_gif(self, tmp_path):
        """Create an animated GIF for testing"""
        frames = []
        for i in range(3):
            img = Image.new("P", (50, 50), color=i * 50)
            palette = list(range(256)) * 3
            img.putpalette(palette)
            frames.append(img)
        
        path = tmp_path / "animated.gif"
        frames[0].save(
            path,
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0,
            format="GIF"
        )
        return str(path)

    def test_palette_chi_square_valid_frame(self):
        """Test palette chi-square on valid frame"""
        img = Image.new("P", (50, 50), color=0)
        palette = list(range(256)) * 3
        img.putpalette(palette)
        
        chi = StatisticalAnalysis.palette_chi_square(img)
        assert isinstance(chi, float)
        assert chi >= 0

    def test_palette_chi_square_no_palette(self):
        """Test palette chi-square on frame without palette"""
        img = Image.new("RGB", (50, 50))
        chi = StatisticalAnalysis.palette_chi_square(img)
        assert chi == 0.0

    def test_pixel_chi_square_valid_frame(self):
        """Test pixel chi-square calculation"""
        img = Image.new("P", (50, 50), color=100)
        chi = StatisticalAnalysis.pixel_chi_square(img)
        assert isinstance(chi, float)
        assert chi >= 0

    def test_gif_palette_entropy(self, static_gif):
        """Test GIF palette entropy calculation"""
        entropies = StatisticalAnalysis.gif_palette_entropy(static_gif)
        assert isinstance(entropies, list)
        assert len(entropies) > 0
        assert all(isinstance(e, float) for e in entropies)

    def test_gif_palette_entropy_nonexistent(self):
        """Test GIF palette entropy with nonexistent file"""
        with pytest.raises(FileNotFoundError):
            StatisticalAnalysis.gif_palette_entropy("nonexistent.gif")

    def test_gif_chi_square_static(self, static_gif):
        """Test chi-square analysis on static GIF"""
        result = StatisticalAnalysis.gif_chi_square(static_gif)
        
        assert "frames_palette" in result
        assert "average_palette" in result
        assert "median_palette" in result
        assert "frames_pixel" in result
        assert "average_pixel" in result
        assert "median_pixel" in result
        
        assert isinstance(result["frames_palette"], list)
        assert isinstance(result["frames_pixel"], list)
        assert len(result["frames_palette"]) > 0
        assert len(result["frames_pixel"]) > 0

    def test_gif_chi_square_animated(self, animated_gif):
        """Test chi-square analysis on animated GIF"""
        result = StatisticalAnalysis.gif_chi_square(animated_gif)
        
        assert len(result["frames_palette"]) == 3
        assert len(result["frames_pixel"]) == 3
        assert result["average_palette"] > 0
        assert result["average_pixel"] > 0

    def test_gif_chi_square_delta(self, static_gif, tmp_path):
        """Test GIF chi-square delta calculation"""

        img = Image.open(static_gif)
        modified_path = tmp_path / "modified.gif"
        img.save(modified_path, format="GIF")
        
        result = StatisticalAnalysis.gif_chi_square_delta(static_gif, str(modified_path))
        
        assert "delta_pixel_per_frame" in result
        assert "delta_pixel_average" in result
        assert "delta_palette_per_frame" in result
        assert "delta_palette_average" in result
        assert isinstance(result["delta_pixel_per_frame"], list)

    def test_gif_entropy_delta(self, static_gif, tmp_path):
        """Test GIF entropy delta calculation"""
        img = Image.open(static_gif)
        modified_path = tmp_path / "modified.gif"
        img.save(modified_path, format="GIF")
        
        result = StatisticalAnalysis.gif_entropy_delta(static_gif, str(modified_path))
        
        assert "per_frame" in result
        assert "average" in result
        assert "median" in result
        assert "max_abs" in result
        assert isinstance(result["per_frame"], list)

    def test_gif_calculate_mse(self, animated_gif, tmp_path):
        """Test GIF MSE calculation"""
        img = Image.open(animated_gif)
        modified_path = tmp_path / "modified.gif"
        img.save(modified_path, format="GIF")
        
        result = StatisticalAnalysis.gif_calculate_mse(animated_gif, str(modified_path))
        
        assert "mse_per_frame" in result
        assert "mse_average" in result
        assert isinstance(result["mse_per_frame"], list)
        assert isinstance(result["mse_average"], float)

    def test_gif_calculate_psnr(self, animated_gif, tmp_path):
        """Test GIF PSNR calculation"""
        img = Image.open(animated_gif)
        modified_path = tmp_path / "modified.gif"
        img.save(modified_path, format="GIF")
        
        result = StatisticalAnalysis.gif_calculate_psnr(animated_gif, str(modified_path))
        
        assert "psnr_per_frame" in result
        assert "psnr_average" in result
        assert isinstance(result["psnr_per_frame"], list)


class TestLSBImageStatistics:
    """Test LSB image quality metrics"""

    @pytest.fixture
    def test_image_pair(self, tmp_path):
        """Create a pair of test images"""
        img1 = Image.new("RGB", (100, 100), color=(128, 128, 128))
        img2 = Image.new("RGB", (100, 100), color=(129, 129, 129))
        
        path1 = tmp_path / "original.png"
        img1.save(path1)
        
        return str(path1), img2

    def test_lsb_calculate_psnr(self, test_image_pair):
        """Test PSNR calculation"""
        cover_path, stego = test_image_pair
        psnr = StatisticalAnalysis.lsb_calculate_psnr(cover_path, stego)
        
        assert isinstance(psnr, float)
        assert psnr > 0

    def test_lsb_calculate_psnr_identical(self, tmp_path):
        """Test PSNR with identical images (should be infinite)"""
        img = Image.new("RGB", (50, 50), color=(100, 100, 100))
        path = tmp_path / "identical.png"
        img.save(path)
        
        psnr = StatisticalAnalysis.lsb_calculate_psnr(str(path), img)
        assert psnr == float("inf")

    def test_lsb_calculate_mse(self, test_image_pair):
        """Test MSE calculation"""
        cover_path, stego = test_image_pair
        mse = StatisticalAnalysis.lsb_calculate_mse(cover_path, stego)
        
        assert isinstance(mse, float)
        assert mse >= 0

    def test_lsb_calculate_mse_identical(self, tmp_path):
        """Test MSE with identical images (should be 0)"""
        img = Image.new("RGB", (50, 50), color=(100, 100, 100))
        path = tmp_path / "identical.png"
        img.save(path)
        
        mse = StatisticalAnalysis.lsb_calculate_mse(str(path), img)
        assert mse == 0.0

    def test_lsb_calculate_histogram_difference(self, test_image_pair):
        """Test histogram difference calculation"""
        cover_path, stego = test_image_pair
        result = StatisticalAnalysis.lsb_calculate_histogram_difference(cover_path, stego)
        
        assert isinstance(result, dict)
        assert "R" in result
        assert "G" in result
        assert "B" in result
        assert "average" in result
        assert all(v >= 0 for v in result.values())

    def test_lsb_calculate_psnr_missing_file(self, tmp_path):
        """Test PSNR with missing cover file"""
        img = Image.new("RGB", (50, 50))
        with pytest.raises(FileNotFoundError):
            StatisticalAnalysis.lsb_calculate_psnr("nonexistent.png", img)

    def test_lsb_dimension_mismatch(self, tmp_path):
        """Test error handling for dimension mismatch"""
        img1 = Image.new("RGB", (50, 50), color=(100, 100, 100))
        img2 = Image.new("RGB", (100, 100), color=(100, 100, 100))
        
        path1 = tmp_path / "small.png"
        img1.save(path1)
        
        with pytest.raises(ImageStatisticsException):
            StatisticalAnalysis.lsb_calculate_psnr(str(path1), img2)


class TestSVGStatistics:
    """Test SVG-specific statistical analysis"""

    @pytest.fixture
    def simple_svg(self, tmp_path):
        """Create a simple SVG file"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
    <circle cx="50" cy="50" r="30" fill="red"/>
</svg>"""
        path = tmp_path / "simple.svg"
        path.write_text(svg_content)
        return str(path)

    @pytest.fixture
    def complex_svg(self, tmp_path):
        """Create a complex SVG with various elements"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
    <rect id="very_long_identifier_name_here" x="10" y="10" width="50" height="50"/>
    <circle class="another_very_long_class_name" cx="100" cy="100" r="40"/>
    <!-- This is a comment -->
    <path d="M 10,10 L 100,100 50,50 Z" fill="green"/>
</svg>"""
        path = tmp_path / "complex.svg"
        path.write_text(svg_content)
        return str(path)

    def test_svg_calculate_element_patterns(self, simple_svg):
        """Test SVG element pattern detection"""
        result = StatisticalAnalysis.svg_calculate_element_patterns(simple_svg)
        
        assert isinstance(result, dict)
        assert "comments" in result
        assert "long_ids" in result
        assert "long_classes" in result
        assert all(isinstance(v, int) for v in result.values())

    def test_svg_calculate_element_patterns_complex(self, complex_svg):
        """Test pattern detection on complex SVG"""
        result = StatisticalAnalysis.svg_calculate_element_patterns(complex_svg)
        
        assert result["long_ids"] > 0 
        assert result["long_classes"] > 0

    def test_svg_calculate_pattern_delta(self, simple_svg, complex_svg):
        """Test SVG pattern delta calculation"""
        result = StatisticalAnalysis.svg_calculate_pattern_delta(simple_svg, complex_svg)
        
        assert isinstance(result, dict)
        assert "comments" in result
        assert "long_ids" in result
        assert "long_classes" in result

    def test_svg_calculate_elements(self, simple_svg):
        """Test SVG element counting"""
        result = StatisticalAnalysis.svg_calculate_elements(simple_svg)
        
        assert isinstance(result, dict)
        assert len(result) > 0
        assert all(isinstance(k, str) and isinstance(v, int) for k, v in result.items())

    def test_svg_calculate_numeric_stats(self, simple_svg):
        """Test SVG numeric statistics"""
        result = StatisticalAnalysis.svg_calculate_numeric_stats(simple_svg)
        
        assert isinstance(result, dict)
        assert "count" in result
        assert "mean" in result
        assert "variance" in result
        assert "min" in result
        assert "max" in result
        assert result["count"] > 0

    def test_svg_calculate_numeric_stats_delta(self, simple_svg, complex_svg):
        """Test SVG numeric stats delta"""
        result = StatisticalAnalysis.svg_calculate_numeric_stats_delta(simple_svg, complex_svg)
        
        assert isinstance(result, dict)
        assert "count" in result

    def test_svg_entropy_bytes_delta(self, simple_svg, tmp_path):
        """Test SVG entropy delta"""

        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="80" fill="red"/>
</svg>"""
        modified_path = tmp_path / "modified.svg"
        modified_path.write_text(svg_content)
        
        delta = StatisticalAnalysis.shannon_entropy_bytes_delta(simple_svg, str(modified_path))
        assert isinstance(delta, float)

    def test_svg_nonexistent_file(self):
        """Test SVG statistics with nonexistent file"""
        with pytest.raises(FileNotFoundError):
            StatisticalAnalysis.svg_calculate_elements("nonexistent.svg")

    def test_svg_invalid_xml(self, tmp_path):
        """Test SVG statistics with invalid XML"""
        invalid_svg = tmp_path / "invalid.svg"
        invalid_svg.write_text("This is not valid XML")
        
        with pytest.raises(ImageStatisticsException):
            StatisticalAnalysis.svg_calculate_elements(str(invalid_svg))


class TestAnalysisWrappers:
    """Test high-level analysis wrapper functions"""

    @pytest.fixture
    def lsb_image(self, tmp_path):
        """Create an LSB test image"""
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        path = tmp_path / "lsb_test.png"
        img.save(path)
        return str(path)

    @pytest.fixture
    def gif_file(self, tmp_path):
        """Create a GIF test file"""
        img = Image.new("P", (50, 50), color=0)
        palette = list(range(256)) * 3
        img.putpalette(palette)
        path = tmp_path / "test.gif"
        img.save(path, format="GIF")
        return str(path)

    @pytest.fixture
    def svg_file(self, tmp_path):
        """Create an SVG test file"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>"""
        path = tmp_path / "test.svg"
        path.write_text(svg_content)
        return str(path)

    def test_analyze_lsb(self, lsb_image):
        """Test complete LSB analysis"""
        result = StatisticalAnalysis.analyze_lsb(lsb_image)
        
        assert isinstance(result, dict)
        assert "R" in result
        assert "G" in result
        assert "B" in result
        assert "average" in result
        assert "median" in result

    def test_analyze_gif(self, gif_file):
        """Test complete GIF analysis"""
        result = StatisticalAnalysis.analyze_gif(gif_file)
        
        assert isinstance(result, dict)
        assert "chi_sq" in result
        assert "palette_entropy" in result

    def test_analyze_svg(self, svg_file):
        """Test complete SVG analysis"""
        result = StatisticalAnalysis.analyze_svg(svg_file)
        
        assert isinstance(result, dict)
        assert "entropy" in result
        assert "numeric_stats" in result
        assert "element_counts" in result
        assert "suspicious_patterns" in result

    def test_compare_gifs(self, gif_file, tmp_path):
        """Test GIF comparison"""
        img = Image.open(gif_file)
        modified_path = tmp_path / "modified.gif"
        img.save(modified_path, format="GIF")
        
        result = StatisticalAnalysis.compare_gifs(gif_file, str(modified_path))
        
        assert isinstance(result, dict)
        assert "mse" in result
        assert "psnr" in result
        assert "chi" in result
        assert "entropy" in result

    def test_compare_svgs(self, svg_file, tmp_path):
        """Test SVG comparison"""
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="20" y="20" width="60" height="60" fill="red"/>
</svg>"""
        modified_path = tmp_path / "modified.svg"
        modified_path.write_text(svg_content)
        
        result = StatisticalAnalysis.compare_svgs(svg_file, str(modified_path))
        
        assert isinstance(result, dict)
        assert "entropy_bytes_delta" in result
        assert "suspicious_patterns_delta" in result
        assert "numeric_stats_delta" in result


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_data_handling(self):
        """Test various functions with empty data"""
        assert StatisticalAnalysis.shannon_entropy_pixels([]) == 0.0
        assert StatisticalAnalysis.shannon_entropy_bytes(b"") == 0.0

    def test_single_value_data(self):
        """Test with single repeated value"""
        data = [42] * 1000
        entropy = StatisticalAnalysis.shannon_entropy_pixels(data)
        assert entropy == 0.0

    def test_file_not_found_errors(self):
        """Test FileNotFoundError handling across functions"""
        with pytest.raises(FileNotFoundError):
            StatisticalAnalysis.analyze_lsb("nonexistent.png")
        
        with pytest.raises(FileNotFoundError):
            StatisticalAnalysis.gif_palette_entropy("nonexistent.gif")
        
        with pytest.raises(FileNotFoundError):
            StatisticalAnalysis.analyze_svg("nonexistent.svg")

    def test_invalid_image_format(self, tmp_path):
        """Test with invalid image format"""
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("This is not an image")
        
        with pytest.raises(Exception):
            StatisticalAnalysis.analyze_lsb(str(invalid_file))


class TestNumericalStability:
    """Test numerical stability and precision"""

    def test_very_large_images(self):
        """Test with large images (memory and performance)"""
        img = Image.new("RGB", (500, 500), color=(100, 100, 100))
        result = StatisticalAnalysis.lsb_chi_square(img)
        
        assert isinstance(result["average"], float)
        assert not np.isnan(result["average"])
        assert not np.isinf(result["average"])

    def test_extreme_pixel_values(self):
        """Test with extreme pixel values"""

        img_black = Image.new("RGB", (100, 100), color=(0, 0, 0))
        result_black = StatisticalAnalysis.lsb_chi_square(img_black)
        assert all(v >= 0 for v in result_black.values() if isinstance(v, (int, float)))
        
        img_white = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result_white = StatisticalAnalysis.lsb_chi_square(img_white)
        assert all(v >= 0 for v in result_white.values() if isinstance(v, (int, float)))

    def test_floating_point_precision(self, tmp_path):
        """Test floating point precision in calculations"""
        img1 = Image.new("RGB", (100, 100), color=(128, 128, 128))
        img2 = Image.new("RGB", (100, 100), color=(128, 128, 129))
        
        path1 = tmp_path / "img1.png"
        img1.save(path1)
        
        psnr = StatisticalAnalysis.lsb_calculate_psnr(str(path1), img2)
        mse = StatisticalAnalysis.lsb_calculate_mse(str(path1), img2)
        
        if mse > 0:
            expected_psnr = 10 * np.log10((255**2) / mse)
            assert psnr == pytest.approx(expected_psnr, rel=1e-6)
