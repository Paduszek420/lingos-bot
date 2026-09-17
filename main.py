import os
import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pl-PL,pl;q=0.9"
})

print("=== DIAGNOSTYKA LOGOWANIA LINGOS.PL ===")

# 1. Pobranie strony logowania
login_url = "https://lingos.pl/login"
res = session.get(login_url)
print(f"[1] Pobranie formularza - Status HTTP: {res.status_code}")

soup = BeautifulSoup(res.text, 'html.parser')

# Weryfikacja obecności Captcha / Cloudflare
if "cloudflare" in res.text.lower() or "recaptcha" in res.text.lower() or "g-recaptcha" in res.text.lower():
    print("[!] OSTRZEŻENIE: Lingos wymaga weryfikacji CAPTCHA / Cloudflare dla adresów IP GitHuba!")

# Szukamy ukrytego tokenu CSRF
token_input = soup.find('input', {'name': '_token'})
token = token_input.get('value', '') if token_input else ''
print(f"[2] Wykryty token CSRF: {'TAK' if token else 'BRAK'}")

# Wysyłamy login w polach 'login' oraz 'email' jednocześnie
payload = {
    'login': USERNAME,
    'email': USERNAME,
    'password': PASSWORD,
    '_token': token
}

print("[3] Wysyłanie formularza logowania...")
post_res = session.post(login_url, data=payload)
print(f"[4] Status odpowiedzi po logowaniu: {post_res.status_code}")
print(f"[5] Adres po przekierowaniu: {post_res.url}")

print("\n--- FRAGMENT ODPOWIEDZI SERWERA ---")
clean_text = " ".join(post_res.text.split())
print(clean_text[:400])
