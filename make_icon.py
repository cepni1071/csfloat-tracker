from PIL import Image, ImageDraw, ImageFont
import os, struct, zlib

def make_icon():
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Yuvarlak köşeli arka plan
    def rounded_rect(draw, xy, radius, fill):
        x0, y0, x1, y1 = xy
        draw.rectangle([x0+radius, y0, x1-radius, y1], fill=fill)
        draw.rectangle([x0, y0+radius, x1, y1-radius], fill=fill)
        draw.ellipse([x0, y0, x0+radius*2, y0+radius*2], fill=fill)
        draw.ellipse([x1-radius*2, y0, x1, y0+radius*2], fill=fill)
        draw.ellipse([x0, y1-radius*2, x0+radius*2, y1], fill=fill)
        draw.ellipse([x1-radius*2, y1-radius*2, x1, y1], fill=fill)

    # Arka plan gradient efekti (koyu lacivert)
    for i in range(size):
        t = i / size
        r = int(10 + t * 15)
        g = int(15 + t * 20)
        b = int(40 + t * 30)
        draw.line([(0, i), (size, i)], fill=(r, g, b, 255))

    rounded_rect(draw, [0, 0, size-1, size-1], 80, None)

    # Turuncu çember halka
    draw.ellipse([60, 60, 452, 452], outline=(255, 140, 0, 255), width=18)

    # Beyaz iç çember
    draw.ellipse([100, 100, 412, 412], outline=(255, 255, 255, 60), width=6)

    # CS sembolü — büyük "CF" yazısı
    try:
        font_big = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 180)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 70)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = font_big

    # "$" sembolü turuncu
    draw.text((size//2, size//2 - 30), "$", font=font_big,
              fill=(255, 160, 30, 255), anchor="mm")

    # Alt yazı
    draw.text((size//2, size//2 + 130), "TRACKER", font=font_small,
              fill=(200, 200, 255, 220), anchor="mm")

    # Boyutlar
    sizes = [16, 32, 64, 128, 256, 512]
    iconset_path = "/tmp/csfloat.iconset"
    os.makedirs(iconset_path, exist_ok=True)

    for s in sizes:
        resized = img.resize((s, s), Image.LANCZOS)
        resized.save(f"{iconset_path}/icon_{s}x{s}.png")
        if s <= 256:
            resized2 = img.resize((s*2, s*2), Image.LANCZOS)
            resized2.save(f"{iconset_path}/icon_{s}x{s}@2x.png")

    os.system(f"iconutil -c icns {iconset_path} -o /Users/cepni/test-claude/csfloat-tracker/icon.icns 2>/dev/null")

    # PNG olarak da kaydet (fallback)
    img.save("/Users/cepni/test-claude/csfloat-tracker/icon.png")
    print("İkon oluşturuldu.")

make_icon()
