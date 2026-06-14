"""Найти путь к pyexpat.pyd."""
from importlib import util
import os

spec = util.find_spec("pyexpat")
if spec and spec.origin:
    print(f"pyexpat найден: {spec.origin}")
    print(f"Размер: {os.path.getsize(spec.origin)} байт")
else:
    print("pyexpat не найден через find_spec")
    # Попробуем через sys.builtin_module_names
    import sys
    print(f"builtin_module_names: {'pyexpat' in sys.builtin_module_names}")
    print(f"stdlib_module_names: {'pyexpat' in getattr(sys, 'stdlib_module_names', [])}")
