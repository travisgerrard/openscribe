from PIL import Image, ImageDraw

colors = {
    "green": "#34c759",
    "orange": "#ff9500",
    "blue": "#007aff",
    "grey": "#8e8e93",
}
size = 64
radius = 28

for name, color in colors.items():
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.ellipse(
        (
            size // 2 - radius,
            size // 2 - radius,
            size // 2 + radius,
            size // 2 + radius,
        ),
        fill=color,
    )
    im.save(f"assets/icon-{name}.png")
print("Tray icons generated: " + ", ".join([f"assets/icon-{name}.png" for name in colors]))
