from PIL import Image, ImageFilter
import numpy as np


def is_monochrome(im: Image.Image, blur_radius: int = 5, sample_size: int = 2048) -> bool:
    """
    High-speed monochrome detection using downscaling and Gaussian blur
    to eliminate sensor noise interference.
    """

    # 1. Downscale and Blur for noise suppression
    w, h = im.size
    ratio = sample_size / max(w, h)
    thumb = im.resize((int(w * ratio), int(h * ratio)), Image.Resampling.BOX)
    thumb = thumb.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # 2. Convert to HSV and extract channels
    hsv_im = thumb.convert('HSV')
    h_arr, s_arr, v_arr = np.array(hsv_im, dtype=np.float32).transpose(2, 0, 1)

    # 3. Mask dark pixels (Value < 30) to avoid Hue jitter in blacks
    mask = v_arr.flatten() > 30
    h_flat = h_arr.flatten()[mask]
    s_flat = s_arr.flatten()[mask]
    v_flat = v_arr.flatten()[mask]

    # 4. Convert to Radial Coordinates
    # Hue (0-255) maps to 0 to 2*pi
    theta = (h_flat / 255.0) * 2 * np.pi
    # Perceptual Saturation (S*V weight as used in your previous logic)
    r = (s_flat * v_flat) / (255.0 ** 2)

    x = r * np.cos(theta)
    y = r * np.sin(theta)

    mean_x = np.mean(x)
    mean_y = np.mean(y)

    dx = x - mean_x
    dy = y - mean_y

    stdev = np.sqrt(np.mean(dx * dx + dy * dy))
    return stdev < 0.02


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