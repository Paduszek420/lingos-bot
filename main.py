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

    print("2. Otwieranie strony logowania...")
    page.goto("https://lingos.pl/h/login", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Wyrzucenie banera z plikami cookie (Cookiebot)
    page.evaluate("""() => {
        const dialog = document.getElementById('CybotCookiebotDialog');
        if (dialog) dialog.remove();
        const overlay = document.getElementById('CybotCookiebotDialogBodyUnderlay');
        if (overlay) overlay.remove();
    }""")

    print("3. Szukanie widocznego pola logowania...")
    # Czekanie bezpośrednio na WIDOCZNE pole do wpisania loginu
    page.wait_for_selector("input[name='login'], input[name='email'], input[type='text']:not([type='hidden'])", state="visible", timeout=15000)

    print("4. Wpisywanie danych logowania...")
    page.fill("input[name='login'], input[name='email'], input[type='text']:not([type='hidden'])", USERNAME)
    page.fill("input[type='password']", PASSWORD)
    page.click("button[type='submit'], input[type='submit']", force=True)
    
    page.wait_for_timeout(3000)

    if "login" in page.url.lower():
        print("[X] BŁĄD LOGOWANIA: Odrzucono dane.")
        browser.close()
        exit(1)

    print("[OK] Zalogowano pomyślnie! Otwieranie lekcji...")

    page.goto("https://lingos.pl/learning/start/0?groupId=19788", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # Usunięcie banera, gdyby pojawił się po przejściu do lekcji
    page.evaluate("""() => {
        const dialog = document.getElementById('CybotCookiebotDialog');
        if (dialog) dialog.remove();
    }""")

    solved = 0
    dictionary = {}

    for step in range(30):
        content = page.content().lower()
        if "koniec" in content or "gratulacje" in content or "brak słówek" in content or "podsumowanie" in content:
            print("[+] Lekcja została w pełni ukończona!")
            break

        ans_input = page.query_selector("input[type='text']:not([readonly]):not([type='hidden'])")
        if not ans_input:
            print("[!] Brak pola do wpisania odpowiedzi. Lekcja dobiegła końca.")
            break

        word_el = page.query_selector(".word-to-translate, h3, strong")
        word_text = word_el.inner_text().strip() if word_el else "słówko"

        answer = dictionary.get(word_text, "")
        
        ans_input.fill(answer)
        wait = random.randint(2, 4)
        print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Czekam {wait}s...")
        time.sleep(wait)

        submit_btn = page.query_selector("button[type='submit'], input[type='submit']")
        if submit_btn:
            submit_btn.click(force=True)
        else:
            ans_input.press("Enter")

        page.wait_for_timeout(2500)

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
