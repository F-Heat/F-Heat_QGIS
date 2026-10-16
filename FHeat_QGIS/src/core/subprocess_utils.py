import os
import sys
import subprocess


def get_clean_env_for_venv() -> dict:
    """Saubere Umgebung für venv-Subprozesse (kein QGIS-Leak)."""
    env = os.environ.copy()
    # PYTHONEXECUTABLE (set by OSGeo4W/QGIS) makes the venv python run as the
    # base interpreter, so pip would install outside the venv
    for var in ['PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE', 'VIRTUAL_ENV',
                'QGIS_PREFIX_PATH', 'QGIS_PLUGINPATH']:
        env.pop(var, None)
    env["PYTHONIOENCODING"] = "utf-8"
    # The venv uses --system-site-packages, which would also include the user
    # site-packages (%APPDATA%\Python) - pip must only see QGIS + venv packages
    env["PYTHONNOUSERSITE"] = "1"
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