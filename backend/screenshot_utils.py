import base64
import io
from PIL import Image
import numpy as np
import cv2

class ScreenshotProcessor:
    @staticmethod
    def decode_base64_screenshot(base64_string: str) -> Image.Image:
        """Convert base64 screenshot to PIL Image"""
        # Input: "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
        # Output: PIL Image object
        
        if base64_string.startswith('data:image'):
            # Remove data URL prefix: "data:image/jpeg;base64,"
            base64_string = base64_string.split(',')[1]
        
        # Decode base64 to binary
        image_data = base64.b64decode(base64_string)
        
        # Create PIL Image from binary data
        image = Image.open(io.BytesIO(image_data))
        return image
    
    @staticmethod
    def preprocess_image_for_llm(image: Image.Image) -> dict:
        """Prepare image for Ollama vision model"""
        # Ollama needs images in base64 format
        
        # 1. Ensure RGB format (not RGBA, grayscale, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 2. Resize if too large (Ollama works better with smaller images)
        max_size = 1024  # Maximum dimension
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # 3. Convert to base64 for Ollama API
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)  # Compress
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "image": img_str,  # Base64 string Ollama can understand
            "width": image.width,
            "height": image.height,
            "format": "jpeg"
        }
    
    @staticmethod
    def extract_text_regions(image: Image.Image) -> list:
        """Use OpenCV to find text regions (fallback if LLM fails)"""
        # Converts image to find where text might be
        # Not used in main flow, but good backup
        
        img_np = np.array(image)  # PIL → NumPy
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)  # Color → Grayscale
        
        # Threshold creates black/white image
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours (connected shapes)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 20 and h > 10:  # Ignore tiny specs
                regions.append({
                    "x": x, "y": y, "width": w, "height": h,
                    "area": w * h
                })
        
        return regions  # List of text region coordinates