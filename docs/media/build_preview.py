"""Build the README phone-frame slideshow from verified synthetic app captures."""
import csv
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CAPTURES = ROOT / 'Spendly_Final_Report_Visuals'
SIZE = (1080, 860)
INK = '#153b34'
GREEN = '#16715f'
SCENES = [
    ('transactions', '02_Chapter5_Application/Fig_5_10_Transaction_Management.png',
     'Every transaction, together.', 'Income, expenses and import sources.\nA clear view of what came in and went out.'),
    ('budgets', '05_Appendix_A_Test_Evidence/Appendix_A8_Budget_Management.png',
     'See where your budget stands.', 'Compare spending with your limits.\nKnow when a category needs attention.'),
    ('forecast', '02_Chapter5_Application/Fig_5_12_LSTM_Forecast_Interface.png',
     'Plan with spending estimates.', 'Weekly estimates from recorded history.\nContext and limitations stay visible.'),
    ('alerts', '02_Chapter5_Application/Fig_5_13_Anomaly_Alert_Review.png',
     'Review unusual spending.', 'Look closer at entries worth reviewing.\nThese are prompts, not fraud findings.'),
    ('recommendations', '02_Chapter5_Application/Fig_5_14_Financial_Recommendations.png',
     'Turn insight into next steps.', 'Practical, rule-based recommendations.\nStart with one manageable action.'),
]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def font(size, bold=False):
    windows = Path('C:/Windows/Fonts') / ('segoeuib.ttf' if bold else 'segoeui.ttf')
    return ImageFont.truetype(str(windows) if windows.exists() else
                              ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'), size)


def main():
    screens = HERE / 'screens'
    screens.mkdir(exist_ok=True)
    provenance_path = HERE / 'sources.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8')) if provenance_path.exists() else {}
    if CAPTURES.exists():
        with (CAPTURES / 'Figure_Manifest.csv').open(encoding='utf-8-sig', newline='') as stream:
            manifest = {row['file_path']: row for row in csv.DictReader(stream)}
        for name, source, *_ in SCENES:
            original = CAPTURES / source
            row = manifest[source]
            assert row['verification_status'] == 'VERIFIED_CONTROLLED_NATIVE_CAPTURE'
            assert digest(original) == row['sha256'], source
            with Image.open(original) as image:
                assert image.size == (1440, 3032)
                image.convert('RGB').resize((648, 1364), Image.Resampling.LANCZOS).save(screens / (name + '.png'), optimize=True)
            provenance[name] = dict(original=source, original_sha256=row['sha256'],
                                    capture_date=row['evidence_date'],
                                    implementation=row['implementation_version'],
                                    preview_source_sha256=digest(screens / (name + '.png')))
        provenance_path.write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')

    base = Image.new('RGB', SIZE)
    draw = ImageDraw.Draw(base)
    for y in range(SIZE[1]):
        t = y / SIZE[1]
        draw.line((0, y, SIZE[0], y), fill=(int(247 - 15*t), int(251 - 6*t), int(248 - 9*t)))
    glow = Image.new('RGBA', SIZE)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((580, -160, 1190, 460), fill=(113, 226, 189, 58))
    gd.ellipse((-150, 630, 420, 1130), fill=(170, 220, 204, 50))
    base = Image.alpha_composite(base.convert('RGBA'), glow.filter(ImageFilter.GaussianBlur(70))).convert('RGB')
    draw = ImageDraw.Draw(base)
    logo = Image.open(ROOT / 'docs/store-assets/spendly-icon-512.png').convert('RGBA')
    logo.thumbnail((58, 58), Image.Resampling.LANCZOS)
    base.paste(logo, (64, 64), logo)
    draw.text((138, 68), 'Spendly', font=font(37, True), fill=INK)
    draw.text((64, 157), 'PERSONAL FINANCE  /  KES', font=font(17, True), fill=GREEN)
    draw.multiline_text((60, 202), 'Your money,\nmade clearer.', font=font(61, True), spacing=1, fill=INK)
    draw.multiline_text((64, 366), 'Track. Understand. Plan.', font=font(24), fill='#58736c')
    draw.rounded_rectangle((64, 423, 596, 425), radius=1, fill='#c8dcd4')
    draw.text((64, 760), 'ANDROID-FIRST  ·  FLUTTER + FLASK', font=font(15, True), fill=GREEN)
    draw.text((64, 789), 'Real app screens · Synthetic demo data', font=font(16), fill='#58736c')

    shadow = Image.new('RGBA', SIZE)
    ImageDraw.Draw(shadow).rounded_rectangle((670, 79, 1024, 817), radius=48, fill=(20, 57, 45, 65))
    base = Image.alpha_composite(base.convert('RGBA'), shadow.filter(ImageFilter.GaussianBlur(22))).convert('RGB')
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((1015, 231, 1021, 316), radius=3, fill='#728780')
    draw.rounded_rectangle((661, 190, 667, 257), radius=3, fill='#728780')
    draw.rounded_rectangle((664, 55, 1018, 805), radius=47, fill='#344940')
    draw.rounded_rectangle((667, 58, 1015, 802), radius=44, fill='#101d19', outline='#73857e', width=1)
    draw.rounded_rectangle((814, 71, 867, 75), radius=2, fill='#52645c')
    draw.ellipse((882, 68, 891, 77), fill='#304740', outline='#566960')
    draw.rounded_rectangle((800, 790, 881, 794), radius=2, fill='#8c9c93')

    mask = Image.new('L', (326, 686), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 325, 685), radius=27, fill=255)
    slides = []
    for index, (name, _, title, description) in enumerate(SCENES):
        source = screens / (name + '.png')
        assert digest(source) == provenance[name]['preview_source_sha256']
        slide = base.copy()
        with Image.open(source) as image:
            slide.paste(image.convert('RGB').resize(mask.size, Image.Resampling.LANCZOS), (678, 92), mask)
        d = ImageDraw.Draw(slide)
        d.text((64, 460), f'0{index+1} / 05', font=font(18, True), fill=GREEN)
        assert d.textbbox((0, 0), title, font=font(31, True))[2] <= 535
        d.text((62, 504), title, font=font(31, True), fill=INK)
        d.multiline_text((64, 562), description, font=font(21), spacing=10, fill='#58736c')
        for step in range(len(SCENES)):
            x = 64 + step * 59
            d.rounded_rectangle((x, 669, x+43, 674), radius=2, fill=GREEN if step == index else '#cbddd4')
        slides.append(slide)

    slides[0].save(HERE / 'spendly-preview.png', optimize=True)
    palette_sheet = Image.new('RGB', (270 * len(slides), 215))
    for index, slide in enumerate(slides):
        palette_sheet.paste(slide.resize((270, 215)), (270 * index, 0))
    palette = palette_sheet.quantize(colors=240)
    colors = palette.getpalette()
    colors += [0] * (768 - len(colors))
    # Sparse red financial warnings must survive the mostly mint/white GIF palette.
    for index, color in enumerate([(181, 69, 60), (190, 62, 51), (243, 226, 224),
                                   (255, 174, 38), (22, 113, 95)], start=240):
        colors[index*3:index*3+3] = color
    palette.putpalette(colors)
    frames, durations = [], []
    for index, slide in enumerate(slides):
        frames.append(slide.quantize(palette=palette, dither=Image.Dither.NONE))
        durations.append(3800)
        for step in range(1, 7):
            blend = Image.blend(slide, slides[(index+1) % len(slides)], step / 7)
            frames.append(blend.quantize(palette=palette, dither=Image.Dither.NONE))
            durations.append(80)
    target = HERE / 'spendly-preview.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=1, comment=b'Actual Spendly acceptance screenshots; synthetic data; animated slideshow, not a live screen recording.')
    with Image.open(target) as check:
        assert check.size == SIZE and check.n_frames == 35 and check.info['loop'] == 0
        total = 0
        for index in range(check.n_frames):
            check.seek(index)
            check.load()
            total += check.info['duration']
        assert total == 21400
        check.seek(7)
        assert any(r > 100 and r > g*1.3 and r > b*1.3
                   for _, (r, g, b) in check.convert('RGB').crop((678, 92, 1004, 778)).getcolors(326*686))
    assert target.stat().st_size < 8_000_000
    print(f'PASS: five source hashes, 35 decodable GIF frames, 21.4-second seamless loop, {target.stat().st_size:,} bytes; static PNG saved.')


if __name__ == '__main__':
    main()
