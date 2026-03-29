from PIL import Image
import numpy as np


def is_monochrome(
        im: Image.Image,
        sat_threshold: int = 20,
        hue_std_threshold: float = 5.0,
        min_color_pixels_ratio: float = 0.02
) -> bool:
    """
    Advanced monochrome detection that handles color shifts (Sepia, Blue-tint, etc.)
    by analyzing Hue variance.

    Args:
        im: PIL Image (converted to RGB internally).
        sat_threshold: Minimum saturation [0-255] to consider a pixel "colored".
        hue_std_threshold: Max standard deviation of Hue allowed for monochrome.
                           Lower is stricter (purely one tint).
        min_color_pixels_ratio: If fewer than 2% of pixels are colored, it's
                                effectively B&W regardless of hue.
    """
    # 1. Convert to HSV
    hsv = im.convert('HSV')
    h, s, v = hsv.split()

    s_arr = np.array(s)
    h_arr = np.array(h)

    # 2. Mask: Only look at pixels that are actually saturated (not gray/white/black)
    # We ignore very desaturated pixels which would randomise the Hue calculation.
    color_mask = s_arr > sat_threshold

    # Total colorful pixels
    num_color_pixels = np.count_nonzero(color_mask)
    total_pixels = s_arr.size
    color_ratio = num_color_pixels / total_pixels

    # If there's almost no color at all, it's definitely monochrome
    if color_ratio < min_color_pixels_ratio:
        return True

    # 3. Analyze Hue Variance of the colored pixels
    relevant_hues = h_arr[color_mask]

    # Circular Standard Deviation: Since Hue 0 and 255 are both "Red",
    # we use a simplified check or shift the range if it wraps around.
    # For comics/scans, a simple Std Dev usually suffices unless the tint is exactly 0.
    hue_std = np.std(relevant_hues)

    # 4. Final Decision
    # If the variance in Hue is very low, the whole page is tinted one color.
    if hue_std < hue_std_threshold:
        return True  # It's Sepia, Blue-tinted, or Green-tinted monochrome

    return False  # It's a multi-color image


def shrink_image(
        input_image_file_path: str,
        output_image_file_path: str,
        quality: int = 80,
        max_height: int = 2560
) -> None:
    """
    Reads an image, handles transparency, resizes if necessary,
    detects monochrome status, and saves as an optimized WebP.

    Args:
        input_image_file_path: Path to the source image (PNG, JPG, etc.)
        output_image_file_path: Path to save the optimized .webp
        quality: WebP compression quality (0-100)
        max_height: Maximum vertical resolution allowed before downscaling
    """
    with Image.open(input_image_file_path) as im:
        # --- 1. Handle Alpha Channel (Transparency) ---
        # Flatten RGBA/LA onto a white background to avoid black-background artifacts
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            im = im.convert("RGBA")
            canvas = Image.new("RGB", im.size, (255, 255, 255))
            canvas.paste(im, mask=im.split()[3])
            im = canvas
        else:
            im = im.convert("RGB")

        # --- 2. Smart Resizing ---
        # Only shrink if the image height exceeds our limit
        width, height = im.size
        if height > max_height:
            ratio = max_height / float(height)
            new_width = int(float(width) * ratio)
            # LANCZOS provides the best detail retention for comic art
            im = im.resize((new_width, max_height), Image.Resampling.LANCZOS)

        # --- 3. Monochrome Detection & Color Space Optimization ---
        # Use our weighted HSV logic to see if we can drop to 1-channel Grayscale
        if is_monochrome(im):
            im = im.convert("L")
            current_sns = 75  # Hint: Simple pages can handle more noise shaping
        else:
            current_sns = 45  # Hint: Maintain more texture for color pages

        # --- 4. Final WebP Export (The "Shrinker" logic) ---
        im.save(
            output_image_file_path,
            "WEBP",
            quality=quality,
            method=6,  # Highest CPU effort for smallest file size
            segments=4,  # Max range hinting blocks
            sns_strength=current_sns,
            lossless=False
        )