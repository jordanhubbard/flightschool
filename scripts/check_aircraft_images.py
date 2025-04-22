import os
from app import create_app, db
from app.models import Aircraft

STATIC_IMAGE_DIR = os.path.join(os.path.dirname(__file__), '../static/images/aircraft')

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

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        check_aircraft_images()
