import os
from app import create_app, db
from app.models import Aircraft
import requests
from duckduckgo_search import DDGS
from PIL import Image

STATIC_IMAGE_DIR = os.path.join(os.path.dirname(__file__), '../static/images/aircraft')
NORMALIZED_SIZE = (400, 300)

def duckduckgo_image_search(query):
    # Use duckduckgo-search package for robust image search
    with DDGS() as ddgs:
        results = list(ddgs.images(query, max_results=3))
        return [r['image'] for r in results]


def normalize_image_size(img_path):
    try:
        with Image.open(img_path) as img:
            img = img.convert('RGB')
            img.thumbnail((NORMALIZED_SIZE[0], NORMALIZED_SIZE[1]), Image.LANCZOS)
            # Create a new blank image (white background)
            new_img = Image.new('RGB', NORMALIZED_SIZE, (255, 255, 255))
            left = (NORMALIZED_SIZE[0] - img.width) // 2
            top = (NORMALIZED_SIZE[1] - img.height) // 2
            new_img.paste(img, (left, top))
            new_img.save(img_path, 'JPEG', quality=90)
            print(f"    Normalized {os.path.basename(img_path)} to {NORMALIZED_SIZE[0]}x{NORMALIZED_SIZE[1]}")
    except Exception as e:
        print(f"    Error normalizing image {img_path}: {e}")


def batch_normalize_all_images():
    print("Batch normalizing all aircraft images...")
    for fname in os.listdir(STATIC_IMAGE_DIR):
        img_path = os.path.join(STATIC_IMAGE_DIR, fname)
        if os.path.isfile(img_path) and fname.lower().endswith(('.jpg', '.jpeg', '.png')):
            normalize_image_size(img_path)


def check_aircraft_images():
    missing = []
    for aircraft in Aircraft.query.all():
        expected_files = []
        if aircraft.image_filename:
            expected_files.append(aircraft.image_filename)
        # Add type-based fallback
        if aircraft.category == 'single_engine_land':
            if aircraft.engine_type == 'piston':
                expected_files.append('cessna172.jpg')
            elif aircraft.engine_type == 'turboprop':
                expected_files.append('tbm930.jpg')
        elif aircraft.category == 'multi_engine_land':
            if aircraft.engine_type == 'piston':
                expected_files.append('baron58.jpg')
            elif aircraft.engine_type == 'turboprop':
                expected_files.append('kingair350.jpg')
            elif aircraft.engine_type == 'jet':
                expected_files.append('citation.jpg')
        expected_files.append('default.jpg')
        found = False
        for fname in expected_files:
            img_path = os.path.join(STATIC_IMAGE_DIR, fname)
            if os.path.exists(img_path) and os.path.getsize(img_path) > 1024:
                found = True
                break
        if not found:
            print(f"Missing image for aircraft: {aircraft.registration} (expected one of: {expected_files})")
            # Try DuckDuckGo image search for the most specific filename (not default)
            for fname in expected_files:
                if fname != 'default.jpg':
                    query = fname.replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('_', ' ')
                    print(f"  DuckDuckGo image search for '{query}':")
                    try:
                        urls = duckduckgo_image_search(query)
                        for idx, url in enumerate(urls):
                            print(f"    [{idx+1}] {url}")
                        if urls:
                            choice = input(f"  Enter number to download and save as {fname} (Enter to skip): ").strip()
                            if choice.isdigit() and 1 <= int(choice) <= len(urls):
                                img_url = urls[int(choice)-1]
                                print(f"    Downloading {img_url} as {fname}...")
                                img_path = os.path.join(STATIC_IMAGE_DIR, fname)
                                try:
                                    resp = requests.get(img_url, timeout=10)
                                    if resp.status_code == 200 and resp.content and len(resp.content) > 1024:
                                        os.makedirs(os.path.dirname(img_path), exist_ok=True)
                                        with open(img_path, 'wb') as f:
                                            f.write(resp.content)
                                        normalize_image_size(img_path)
                                        print(f"    Saved {fname}.")
                                    else:
                                        print(f"    Failed to download or image too small.")
                                except Exception as e:
                                    print(f"    Error downloading image: {e}")
                            else:
                                print(f"    Skipped.")
                    except Exception as e:
                        print(f"    [Error searching DuckDuckGo: {e}]")
                    break

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        batch_normalize_all_images()
        check_aircraft_images()
