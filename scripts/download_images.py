#!/usr/bin/env python3
import os
import requests
from PIL import Image
from io import BytesIO
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default aircraft images to download
AIRCRAFT_IMAGES = {
    'cessna172.jpg': 'https://upload.wikimedia.org/wikipedia/commons/0/09/Cessna_172S_Skyhawk_SP%2C_Private_JP6817606.jpg',
    'tbm930.jpg': 'https://upload.wikimedia.org/wikipedia/commons/7/7d/Daher_TBM_930_at_AERO_Friedrichshafen_2019.jpg',
    'baron58.jpg': 'https://upload.wikimedia.org/wikipedia/commons/5/54/Beechcraft_Baron_58_N58DF.jpg',
    'kingair350.jpg': 'https://upload.wikimedia.org/wikipedia/commons/c/c8/Beechcraft_King_Air_350i_OK-HWK.jpg',
    'citation.jpg': 'https://upload.wikimedia.org/wikipedia/commons/0/02/Cessna_525A_Citation_CJ2%2B%2C_Private_JP7683833.jpg',
    'default.jpg': 'https://upload.wikimedia.org/wikipedia/commons/8/82/Generic_Aircraft_Silhouette.svg'
}

def download_and_save_image(url, filename, target_size=(800, 600)):
    """Download an image from URL, resize it, and save it as JPEG."""
    logger.info(f"Downloading {url} to {filename}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        logger.info(f"Downloaded {len(response.content)} bytes")
        
        # Open the image using PIL
        img = Image.open(BytesIO(response.content))
        logger.info(f"Opened image: size={img.size}, mode={img.mode}")
        
        # Convert to RGB if necessary (for PNG with transparency)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            logger.info("Converted image to RGB mode")
        
        # Resize image while maintaining aspect ratio
        img.thumbnail(target_size, Image.Resampling.LANCZOS)
        logger.info(f"Resized image to {img.size}")
        
        # Save as JPEG with good quality
        img.save(filename, 'JPEG', quality=85)
        logger.info(f"Successfully saved {filename}")
        return True
    except Exception as e:
        logger.error(f"Error downloading {filename} from {url}: {str(e)}")
        return False

def main():
    # Create the aircraft images directory if it doesn't exist
    image_dir = os.path.join('app', 'static', 'images', 'aircraft')
    os.makedirs(image_dir, exist_ok=True)
    logger.info(f"Using image directory: {image_dir}")
    
    # Download each image
    for filename, url in AIRCRAFT_IMAGES.items():
        filepath = os.path.join(image_dir, filename)
        if not os.path.exists(filepath):
            logger.info(f"Downloading {filename}...")
            download_and_save_image(url, filepath)
        else:
            logger.info(f"Skipping {filename} - already exists")

if __name__ == '__main__':
    main()
