from PIL import Image, ImageDraw, ImageFont


def create_icon():
    # Define the size of the icon
    size = (256, 256)

    # Create a new image with a transparent background
    image = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    # Draw a blue circle that fills most of the image
    circle_bounds = [20, 20, 236, 236]  # left, top, right, bottom
    circle_color = (30, 144, 255, 255)  # DodgerBlue color
    draw.ellipse(circle_bounds, fill=circle_color)

    # Add a white letter "D" in the center of the circle
    text = "D"
    try:
        # Try to load a TrueType font. Adjust the font path as needed.
        font = ImageFont.truetype("arial.ttf", 140)
    except IOError:
        # Fallback if the TrueType font is not found.
        font = ImageFont.load_default()

    # Use textbbox to get the bounding box of the text.
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (size[0] - text_width) // 2
    text_y = (size[1] - text_height) // 2

    text_color = (255, 255, 255, 255)  # white
    draw.text((text_x, text_y), text, fill=text_color, font=font)

    # Save the image as icon.png
    image.save("icon.png")
    print("icon.png has been created!")


if __name__ == "__main__":
    create_icon()
