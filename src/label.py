from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import qrcode
from bambuddy_api import qr_link

FORMATS = {'40 × 30 mm (getestet)': (384, 288), '50 × 30 mm (Test)': (384, 230), '50 × 40 mm (Test)': (384, 307)}
DEFAULT_FORMAT = next(iter(FORMATS))

def font(size, bold=False):
    name = 'arialbd.ttf' if bold else 'arial.ttf'
    return ImageFont.truetype(str(Path('C:/Windows/Fonts') / name), size)


def fitted_text(draw, value, max_width, start_size, min_size=13, bold=False):
    value = str(value or '-').strip()
    for size in range(start_size, min_size - 1, -1):
        f = font(size, bold)
        if draw.textbbox((0, 0), value, font=f)[2] <= max_width:
            return value, f
    f = font(min_size, bold)
    original = value
    while value and draw.textbbox((0, 0), value + '…', font=f)[2] > max_width:
        value = value[:-1]
    return (value + '…' if value != original else value), f


def render_label(spool, qr_base, fmt):
    spool_id = str(spool.get('id', '?'))
    material = str(spool.get('material') or '-')
    subtype = str(spool.get('subtype') or '').strip()
    if subtype:
        material += ' ' + subtype
    image = Image.new('RGB', (384, 288), 'white')
    draw = ImageDraw.Draw(image)
    entries = [(spool.get('brand'), 14, 25, True), (material, 54, 24, True),
               (spool.get('color_name'), 101, 26, True),
               (spool.get('storage_location'), 145, 19, False)]
    for value, y, size, bold in entries:
        text, f = fitted_text(draw, value, 175, size, 13, bold)
        draw.text((50, y), text, font=f, fill='black')
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(qr_link(qr_base, spool_id))
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color='black', back_color='white').convert('RGB')
    qr_image = qr_image.resize((116, 116), Image.Resampling.NEAREST)
    image.paste(qr_image, (232, 75))
    number, f = fitted_text(draw, '#' + spool_id, 260, 76, 35, True)
    draw.text((50, 165), number, font=f, fill='black')
    size = FORMATS[fmt]
    if size != (384, 288):
        # Experimentell: proportional an andere Etikettenformate anpassen.
        image = image.resize(size, Image.Resampling.NEAREST)
    return image


