import os
import time
import random
import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

print(f"--> Odczytane dane z Secrets: USER='{USERNAME}', PASS={'***' if PASSWORD else 'BRAK!'}")

if not USERNAME or not PASSWORD:
    print("[X] BŁĄD: GitHub nie przekazał danych logowania do Pythona! Sprawdź plik bot.yml.")
    exit(1)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8"
})

LOGIN_URL = "https://lingos.pl/h/login"
START_URL = "https://lingos.pl/learning/start/0?groupId=19788"

try:
    print("1. Pobieranie strony logowania...")
    res = session.get(LOGIN_URL)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    token_input = soup.find('input', {'name': '_token'})
    token = token_input.get('value', '') if token_input else ''
    print(f"--> Pobrano CSRF Token: {bool(token)}")

    payload = {
        'login': USERNAME,
        'password': PASSWORD,
        '_token': token
    }
    
    print("2. Wysyłanie formularza logowania...")
    post_res = session.post(LOGIN_URL, data=payload)
    print(f"--> Kod odpowiedzi serwera: {post_res.status_code}")
    print(f"--> URL po zalogowaniu: {post_res.url}")

    if "login" in post_res.url.lower() and "Moje grupy" not in post_res.text:
        print("[X] BŁĄD LOGOWANIA: Serwer przekierował z powrotem do logowania. Sprawdź poprawność loginu/hasła.")
        exit(1)

    print("[OK] Zalogowano! Otwieranie lekcji...")
    page = session.get(START_URL)
    
    if page.status_code == 200:
        print("[+] Strona lekcji załadowana pomyślnie!")
    else:
        print(f"[X] Błąd ładowania lekcji, status: {page.status_code}")
        exit(1)

except Exception as e:
    print(f"[X] Błąd krytyczny: {e}")
    exit(1)
