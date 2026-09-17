import os
import time
import random
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

if not USERNAME or not PASSWORD:
    print("[X] BŁĄD: Brak danych w Secrets!")
    exit(1)

with sync_playwright() as p:
    print("1. Uruchamianie wirtualnej przeglądarki Chrome...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    print("2. Logowanie...")
    page.goto("https://lingos.pl/h/login")
    page.wait_for_selector("input", timeout=10000)

    # Wpisywanie danych logowania
    page.fill("input[name='login'], input[name='email'], input[type='text']", USERNAME)
    page.fill("input[type='password']", PASSWORD)
    page.click("button[type='submit'], input[type='submit']")
    
    page.wait_for_timeout(3000)

    if "login" in page.url.lower():
        print("[X] BŁĄD LOGOWANIA: Odrzucono dane.")
        browser.close()
        exit(1)

    print(f"[OK] Zalogowano! Otwieranie lekcji...")

    # Wejście bezpośrednio w link lekcji z Twojej grupy
    page.goto("https://lingos.pl/learning/start/0?groupId=19788")
    page.wait_for_timeout(3000)

    solved = 0
    dictionary = {}

    for step in range(30):
        content = page.content().lower()
        if "koniec" in content or "gratulacje" in content or "brak słówek" in content or "podsumowanie" in content:
            print("[+] Lekcja została w pełni ukończona!")
            break

        ans_input = page.query_selector("input[type='text']:not([readonly])")
        if not ans_input:
            print("[!] Brak pola do wpisania odpowiedzi. Lekcja dobiegła końca.")
            break

        # Pobieranie tekstu słówka do przetłumaczenia
        word_el = page.query_selector(".word-to-translate, h3, strong")
        word_text = word_el.inner_text().strip() if word_el else "słówko"

        answer = dictionary.get(word_text, "")
        
        # Fizyczne wpisywanie odpowiedzi i odczekanie
        ans_input.fill(answer)
        wait = random.randint(2, 4)
        print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Czekam {wait}s...")
        time.sleep(wait)

        # Kliknięcie Enter / Wyślij
        submit_btn = page.query_selector("button[type='submit'], input[type='submit']")
        if submit_btn:
            submit_btn.click()
        else:
            ans_input.press("Enter")

        page.wait_for_timeout(2500)

        # Pobieranie poprawnej odpowiedzi po błędzie
        correct_el = page.query_selector(".correct-answer, .alert-success")
        if correct_el:
            dictionary[word_text] = correct_el.inner_text().strip()

        solved += 1

    if solved == 0:
        print("[X] Skrypt nie rozwiązał żadnego słówka!")
        browser.close()
        exit(1)

    print(f"=== SUKCES: Zaliczone słówka/kroki: {solved} ===")
    browser.close()
