from PIL import Image, ImageDraw

def create_image(filename, color, size):
    img = Image.new('RGB', size, color=color)
    d = ImageDraw.Draw(img)
    d.text((10,10), "AG", fill=(255,255,255))
    img.save(f"frontend/assets/{filename}")

create_image("icon.png", "#CCFF00", (1024, 1024))
create_image("splash.png", "#050505", (1242, 2436))
create_image("adaptive-icon.png", "#CCFF00", (1024, 1024))
create_image("favicon.png", "#CCFF00", (48, 48))
print("Assets created.")
