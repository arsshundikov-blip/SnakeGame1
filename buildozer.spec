[app]

# (str) Title of your application
title = Snakegame1

# (str) Package name
package.name = snakegame1

# (str) Package domain (needed for android/ios packaging)
package.domain = org.shipit

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,txt,json,html,js,css,mp3,wav,ogg,gif,xml

# (list) Source files to exclude
source.exclude_exts = spec,pyc,pyo

# (list) List of directory to exclude
source.exclude_dirs = tests, bin, venv, .venv, .git, .github, dist, build, __pycache__

# (str) Application versioning
version = 0.1.0

# (list) Application requirements (comma separated)
# ФИКС: 3.13.9 (последняя для Kivy 2.3.1) + библиотеки, чтобы обойти баг с Python 3.14
requirements = python3==3.13.9,hostpython3==3.13.9,kivy==2.3.1,openssl,sqlite3,pyjnius,android,setuptools,certifi,charset-normalizer,idna,urllib3,requests

# (str) Supported orientation
orientation = landscape

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

#------------------------------------------------------------------------------
# Android specific
#------------------------------------------------------------------------------

android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.logcat_filters = *:S python:D

#------------------------------------------------------------------------------
# Buildozer settings
#------------------------------------------------------------------------------

[buildozer]

log_level = 2
warn_on_root = 0
