"""Generate CommHub icon (.ico) for PyInstaller packaging."""

from PIL import Image, ImageDraw, ImageFont

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Rounded-rect background (blue-ish)
margin = 16
draw.rounded_rectangle(
    [margin, margin, SIZE - margin, SIZE - margin],
    radius=40,
    fill=(59, 130, 246, 255),
)

# "CH" text
try:
    font = ImageFont.truetype("segoeui.ttf", 100)
except (OSError, IOError):
    font = ImageFont.load_default()

text = "CH"
bbox = draw.textbbox((0, 0), text, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
tx = (SIZE - tw) // 2
ty = (SIZE - th) // 2 - 4
draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

img.save("app.ico", format="ICO", sizes=[(256, 256)])
print("Created app.ico")
