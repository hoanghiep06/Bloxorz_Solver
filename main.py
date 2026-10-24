import builtins
import os
import sys
import typing

# Bổ sung typing cho core khi chạy
builtins.List = typing.List
builtins.Tuple = typing.Tuple

try:
    from src.gui.game_app import main
except ImportError:
    venv_py = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_py) and sys.executable != venv_py:
        import subprocess
        sys.exit(subprocess.call([venv_py] + sys.argv))
    raise

if __name__ == "__main__":
    main()
