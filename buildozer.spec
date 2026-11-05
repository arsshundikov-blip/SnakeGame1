[app]

title = Snakegame1
package.name = snakegame1
package.domain = org.shipit

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,txt,json,html,js,css,mp3,wav,ogg,gif,xml
source.exclude_exts = spec,pyc,pyo
source.exclude_dirs = tests, bin, venv, .venv, .git, .github, dist, build, __pycache__

version = 0.1.0

# УБРАЛИ ВЕРСИЮ У pyjnius и оставили только arm64-v8a
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,openssl,sqlite3,pyjnius,setuptools,certifi,charset-normalizer,idna,urllib3,requests

orientation = landscape
fullscreen = 0

android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

# ОСТАВИЛИ ТОЛЬКО СОВРЕМЕННУЮ АРХИТЕКТУРУ
android.archs = arm64-v8a
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 0
