"""Найти путь к ft2font.pyd (C-расширение matplotlib)."""
from importlib import util
import os

spec = util.find_spec("matplotlib.ft2font")
if spec and spec.origin:
    print(f"ft2font найден: {spec.origin}")
    print(f"Размер: {os.path.getsize(spec.origin)} байт")
else:
    print("ft2font не найден через find_spec")
    # Поищем в site-packages
    import matplotlib
    mpl_dir = os.path.dirname(matplotlib.__file__)
    print(f"Папка matplotlib: {mpl_dir}")
    for f in os.listdir(mpl_dir):
        if 'ft2' in f.lower():
            print(f"  Найден: {os.path.join(mpl_dir, f)}")
