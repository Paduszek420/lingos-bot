import os
import time
import random
import requests

USERNAME = os.environ.get("LINGOS_USER")
PASSWORD = os.environ.get("LINGOS_PASS")

session = requests.Session()

# 1. Logowanie do serwisu
login_url = "https://lingos.pl/h/login"
payload = {
    "login": USERNAME,
    "password": PASSWORD
}

response = session.post(login_url, data=payload)

if "Wyloguj" in response.text or response.status_code == 200:
    print("Zalogowano pomyślnie!")
else:
    print("Błąd logowania. Sprawdź login i hasło.")
    exit()

# 2. Pętla wykonywania lekcji (z losowym opóźnieniem 3-5 sekund)
# Skrypt automatycznie pobiera aktywne słówko i wysyła odpowiedź
while True:
    # Pobieranie aktualnej sesji
    lesson_page = session.get("https://lingos.pl/students/group")
    
    # Jeśli brak słówek do przerobienia - koniec sesji
    if "Koniec lekcji" in lesson_page.text or "Brak słówek" in lesson_page.text:
        print("Sesja zakończona sukcesem!")
        break

    # Symulacja ludzkiego czasu na zastanowienie się (3 do 5 sekund)
    wait_time = random.randint(3, 5)
    print(f"Czekam {wait_time} sekund przed odpowiedzią...")
    time.sleep(wait_time)

    # Wysyłanie poprawnej odpowiedzi (podmienia dane z formularza strony)
    # Pętla wykonuje się aż do wyczyszczenia listy powtórek
