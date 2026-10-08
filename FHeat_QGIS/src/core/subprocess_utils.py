import os
import sys
import subprocess


def get_clean_env_for_venv() -> dict:
    """Saubere Umgebung für venv-Subprozesse (kein QGIS-Leak)."""
    env = os.environ.copy()
    for var in ['PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV',
                'QGIS_PREFIX_PATH', 'QGIS_PLUGINPATH']:
        env.pop(var, None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def get_subprocess_kwargs() -> dict:
    """Windows: kein sichtbares cmd-Fenster."""
    kwargs = {}
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs