"""
Генерация иконки AppMonitor без PyQt5 (только PIL).
"""
from PIL import Image, ImageDraw

def create_icon(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size // 8
    # Корпус монитора
    body = [margin, margin, size - margin, size - margin - size // 6]
    draw.rounded_rectangle(body, radius=size//12, fill='#1a1a2e', outline='#0078D4', width=max(1, size//32))

    # Экран
    sm = size // 12
    screen = [body[0]+sm, body[1]+sm, body[2]-sm, body[3]-sm]
    draw.rounded_rectangle(screen, radius=size//20, fill='#16213e')

    # График
    chart_w = screen[2] - screen[0]
    chart_h = screen[3] - screen[1]
    cx, cy = screen[0], screen[1]
    points = [
        (cx + chart_w * 0.05, cy + chart_h * 0.85),
        (cx + chart_w * 0.20, cy + chart_h * 0.60),
        (cx + chart_w * 0.35, cy + chart_h * 0.75),
        (cx + chart_w * 0.50, cy + chart_h * 0.35),
        (cx + chart_w * 0.65, cy + chart_h * 0.50),
        (cx + chart_w * 0.80, cy + chart_h * 0.20),
        (cx + chart_w * 0.95, cy + chart_h * 0.40),
    ]
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill='#00d2ff', width=max(1, size//32))
    for px, py in points:
        r = max(1, size // 32)
        draw.ellipse([px-r, py-r, px+r, py+r], fill='#00d2ff')

    # Подставка
    stand_top = body[3]
    stand_bottom = size - margin
    scx = size // 2
    sw = size // 6
    draw.rectangle([scx-sw//4, stand_top, scx+sw//2, stand_bottom], fill='#1a1a2e', outline='#0078D4', width=max(1, size//32))
    draw.rounded_rectangle([scx-sw, stand_bottom-size//16, scx+sw, stand_bottom], radius=size//32, fill='#1a1a2e', outline='#0078D4', width=max(1, size//32))

    return img

sizes = [16, 32, 48, 64, 128, 256]
images = [create_icon(s) for s in sizes]
images[0].save('app_icon.ico', format='ICO', sizes=[(s,s) for s in sizes], append_images=images[1:])
print('Icon saved: app_icon.ico')
