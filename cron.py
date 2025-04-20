import time
import random
import requests
import platform
import subprocess

def prevent_sleep():
    """Функція для запобігання переходу комп'ютера в режим сну"""
    system = platform.system()
    
    if system == "Windows":
        # Для Windows використовуємо subprocess для виклику PowerShell команди
        subprocess.call("powershell -command \"$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys('{F15}')\"", shell=True)
    elif system == "Darwin":  # macOS
        # Для macOS використовуємо caffeinate
        subprocess.call("caffeinate -u -t 3", shell=True)
    elif system == "Linux":
        # Для Linux використовуємо xdg-screensaver
        subprocess.call("xdg-screensaver reset", shell=True)
    else:
        print(f"Непідтримувана операційна система: {system}")

def make_http_request():
    """Функція для виконання HTTP запиту"""
    try:
        response = requests.get("http://localhost:5000/api/scrape/next")
        print(f"HTTP запит виконано, статус: {response.status_code}, час: {time.strftime('%H:%M:%S')}")
        return response.status_code
    except Exception as e:
        print(f"Помилка при виконанні HTTP запиту: {e}")
        return None

def main():
    print("Скрипт запущено. Натисніть Ctrl+C для завершення.")
    try:
        while True:
            # Запобігаємо переходу в режим сну
            prevent_sleep()
            
            # Виконуємо HTTP запит
            make_http_request()
            
            # Затримка від 20 до 30 секунд
            delay = random.randint(20, 30)
            print(f"Наступний запит через {delay} секунд...")
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\nСкрипт зупинено користувачем.")

if __name__ == "__main__":
    main()