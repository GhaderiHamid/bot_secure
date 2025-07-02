#!/usr/bin/env bash

# نصب محیط پایتون مشخص به‌جای نسخه پیش‌فرض Render
pyenv install 3.11.8 -s
pyenv global 3.11.8

# نصب پکیج‌ها
pip install --upgrade pip
pip install -r requirements.txt