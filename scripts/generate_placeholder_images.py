from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_image(width, height, text, output_path):
    """Create a placeholder image with text."""
    # Create a new image with a light gray background
    image = Image.new('RGB', (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(image)
    
    # Add text
    try:
        font = ImageFont.truetype("Arial", 24)
    except IOError:
        font = ImageFont.load_default()
    
    # Calculate text position
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw text
    draw.text((x, y), text, fill=(100, 100, 100), font=font)
    
    # Save image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path)

def main():
    # Create placeholder images for the home page
    create_placeholder_image(1920, 1080, "Hero Background", "app/static/images/hero-bg.jpg")
    create_placeholder_image(400, 300, "Private Pilot Training", "app/static/images/private_pilot.jpg")
    create_placeholder_image(400, 300, "Instrument Rating", "app/static/images/instrument.jpg")
    create_placeholder_image(400, 300, "Commercial Pilot", "app/static/images/commercial.jpg")
    
    # Create placeholder images for testimonials
    create_placeholder_image(200, 200, "Emily Johnson", "app/static/images/testimonials/testimonial1.jpg")
    create_placeholder_image(200, 200, "Michael Chen", "app/static/images/testimonials/testimonial2.jpg")
    create_placeholder_image(200, 200, "Sarah Williams", "app/static/images/testimonials/testimonial3.jpg")
    
    # Create placeholder images for about page
    create_placeholder_image(800, 600, "Mission", "app/static/images/mission.jpg")
    create_placeholder_image(800, 600, "History", "app/static/images/history.jpg")
    create_placeholder_image(400, 400, "Chief Instructor", "app/static/images/chief_instructor.jpg")
    create_placeholder_image(400, 400, "Maintenance Manager", "app/static/images/maintenance.jpg")
    create_placeholder_image(400, 400, "Operations Manager", "app/static/images/operations.jpg")
    
    # Create placeholder images for training page
    create_placeholder_image(800, 600, "PPL Training", "app/static/images/ppl-training.jpg")
    create_placeholder_image(800, 600, "IR Training", "app/static/images/ir-training.jpg")
    create_placeholder_image(800, 600, "CPL Training", "app/static/images/cpl-training.jpg")

if __name__ == "__main__":
    main() 