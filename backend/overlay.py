from PIL import Image, ImageDraw, ImageFont

def overlay_text(image_path: str, text: str) -> str:
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype("NanumGothic.ttf", 40)

    draw.text((50, 50), text, font=font, fill="white")

    output_path = "output.png"
    img.save(output_path)

    return output_path