from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image():
    """Create a test image with shapes and text"""
    # Create new image with white background
    width = 800
    height = 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw shapes
    # Blue rectangle
    draw.rectangle([300, 200, 500, 400], fill='blue')
    # Red circle
    draw.ellipse([100, 100, 200, 200], fill='red')
    
    # Add text
    text = "AWS Rekognition Test"
    # Use default font since custom fonts might not be available
    font = ImageFont.load_default()
    draw.text((width/3, height/3), text, fill='black', font=font)
    
    # Save the image
    filename = 'test_image.jpg'
    image.save(filename, 'JPEG')
    print(f"Created test image: {filename}")
    return filename
