"""Проверить логи обновления."""
import os
import glob

# Проверяем разные возможные расположения
paths = [
    r"D:\logs",
    os.path.join(os.environ.get("APPDATA", ""), "AppMonitor", "logs"),
    r"C:\code\AppMonitor\logs",
]

for p in paths:
    if os.path.exists(p):
        print(f"Папка {p}: существует")
        files = glob.glob(os.path.join(p, "update_*.log"))
        if files:
            for f in sorted(files, reverse=True)[:3]:
                size = os.path.getsize(f)
                print(f"  {f} ({size} байт)")
                if size > 0:
                    with open(f, "r", encoding="utf-8", errors="replace") as fh:
                        lines = fh.readlines()
                        print(f"    Последние 10 строк:")
                        for line in lines[-10:]:
                            print(f"    {line.rstrip()}")
        else:
            print("  update_*.log не найдены")
    else:
        print(f"Папка {p}: не существует")
