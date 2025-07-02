FROM python:3.11-slim

# ست کردن encoding
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# نصب ابزارهای پایه و کتابخانه‌ها
RUN apt-get update && apt-get install -y build-essential gcc && \
    pip install --upgrade pip

# کپی فایل‌های پروژه
WORKDIR /app
COPY . /app

# نصب پکیج‌ها
RUN pip install -r requirements.txt

# پورت و اجرای برنامه
EXPOSE 8443
CMD ["python", "main.py"]