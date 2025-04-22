import os
from app import create_app, db
from app.models import Aircraft
import requests

STATIC_IMAGE_DIR = os.path.join(os.path.dirname(__file__), '../static/images/aircraft')

def duckduckgo_image_search(query):
    # Use DuckDuckGo's unofficial API to get image results
    url = "https://duckduckgo.com/"
    params = {"q": query}
    res = requests.post(url, data=params)
    search_obj = res.text
    vqd = None
    for line in search_obj.splitlines():
        if 'vqd=' in line:
            vqd = line.split('vqd=')[1].split('&')[0].replace("'", "")
            break
    if not vqd:
        return []
    headers = {"User-Agent": "Mozilla/5.0"}
    img_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={query}&vqd={vqd}"
    imgs = requests.get(img_url, headers=headers).json()
    urls = [img['image'] for img in imgs.get('results', [])]
    return urls[:3]


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
                        for url in urls:
                            print(f"    {url}")
                    except Exception as e:
                        print(f"    [Error searching DuckDuckGo: {e}]")
                    break

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        check_aircraft_images()
