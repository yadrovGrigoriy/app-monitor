"""Найти все C-расширения matplotlib (.pyd)."""
import os
import matplotlib

mpl_dir = os.path.dirname(matplotlib.__file__)
print(f"Папка matplotlib: {mpl_dir}")
print()
for f in sorted(os.listdir(mpl_dir)):
    if f.endswith('.pyd'):
        full = os.path.join(mpl_dir, f)
        size = os.path.getsize(full)
        print(f"  {f}  ({size / 1024:.1f} KB)")
