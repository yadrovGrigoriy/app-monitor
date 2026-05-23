"""Simple icon generator - no encoding issues."""
import sys, os
sys.path.insert(0, '.')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QRect
from PIL import Image
from io import BytesIO

def draw_icon(size):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    margin = size // 8
    body_rect = QRect(margin, margin, size - 2*margin, size - 2*margin - size//6)
    painter.setPen(QPen(QColor('#0078D4'), max(1, size//32)))
    painter.setBrush(QColor('#1a1a2e'))
    painter.drawRoundedRect(body_rect, size//12, size//12)
    screen_margin = size//12
    screen_rect = QRect(body_rect.x()+screen_margin, body_rect.y()+screen_margin,
                        body_rect.width()-2*screen_margin, body_rect.height()-2*screen_margin)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('#16213e'))
    painter.drawRoundedRect(screen_rect, size//20, size//20)
    painter.setPen(QPen(QColor('#00d2ff'), max(1, size//32)))
    painter.setBrush(Qt.NoBrush)
    chart_w, chart_h = screen_rect.width(), screen_rect.height()
    cx, cy = screen_rect.x(), screen_rect.y()
    points = [(cx+chart_w*0.05, cy+chart_h*0.85), (cx+chart_w*0.20, cy+chart_h*0.60),
              (cx+chart_w*0.35, cy+chart_h*0.75), (cx+chart_w*0.50, cy+chart_h*0.35),
              (cx+chart_w*0.65, cy+chart_h*0.50), (cx+chart_w*0.80, cy+chart_h*0.20),
              (cx+chart_w*0.95, cy+chart_h*0.40)]
    for i in range(len(points)-1):
        painter.drawLine(int(points[i][0]), int(points[i][1]), int(points[i+1][0]), int(points[i+1][1]))
    painter.setBrush(QColor('#00d2ff'))
    for px, py in points:
        painter.drawEllipse(int(px)-1, int(py)-1, 3, 3)
    stand_top = body_rect.bottom()
    stand_bottom = size - margin
    scx = size // 2
    sw = size // 6
    painter.setPen(QPen(QColor('#0078D4'), max(1, size//32)))
    painter.setBrush(QColor('#1a1a2e'))
    painter.drawRect(scx-sw//4, stand_top, sw//2, stand_bottom-stand_top)
    painter.drawRoundedRect(scx-sw, stand_bottom-size//16, sw*2, size//16, size//32, size//32)
    painter.end()
    return pixmap

sizes = [16, 32, 48, 64, 128, 256]
images = []
for s in sizes:
    pixmap = draw_icon(s)
    ba = BytesIO()
    pixmap.save(ba, 'PNG')
    ba.seek(0)
    images.append(Image.open(ba))
images[0].save('app_icon.ico', format='ICO', sizes=[(s,s) for s in sizes], append_images=images[1:])
print('Icon saved: app_icon.ico')
