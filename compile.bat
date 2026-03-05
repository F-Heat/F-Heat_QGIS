@echo off
call "C:\Program Files\QGIS 3.34.10\bin\o4w_env.bat"
call "C:\Program Files\QGIS 3.34.10\qt5_env.bat"
call "C:\Program Files\QGIS 3.34.10\py3_env.bat"

@echo on
pyrcc5 -o resources.py resources.qrc