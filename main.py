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
    print("1. Uruchamianie przeglądarki...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    print("2. Logowanie do Lingos.pl...")
    page.goto("https://lingos.pl/h/login", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Usuwanie okna zgody na cookies
    page.evaluate("""() => {
        const dialog = document.getElementById('CybotCookiebotDialog');
        if (dialog) dialog.remove();
        const overlay = document.getElementById('CybotCookiebotDialogBodyUnderlay');
        if (overlay) overlay.remove();
    }""")

    page.wait_for_selector("input[name='login'], input[name='email'], input[type='text']:not([type='hidden'])", state="visible", timeout=15000)
    page.fill("input[name='login'], input[name='email'], input[type='text']:not([type='hidden'])", USERNAME)
    page.fill("input[type='password']", PASSWORD)
    page.click("button[type='submit'], input[type='submit']", force=True)
    page.wait_for_timeout(3000)

    if "login" in page.url.lower():
        print("[X] BŁĄD LOGOWANIA: Niepoprawne dane.")
        browser.close()
        exit(1)

    print(f"[OK] Zalogowano pomyślnie. Szukanie aktywnej lekcji...")

    # 3. Dynamiczne szukanie przycisku rozpoczęcia lekcji na pulpicie
    lesson_link = page.query_selector("a[href*='/learning/start'], a[href*='/learning/'], a.btn-primary")
    
    if lesson_link:
        start_href = lesson_link.get_attribute("href")
        print(f"--> Znaleziono lekcję pod adresem: {start_href}")
        page.goto("https://lingos.pl" + start_href if start_href.startswith("/") else start_href, wait_until="domcontentloaded")
    else:
        print("--> Brak bezpośredniego linku na pulpicie, próba wejścia przez stronę studenta...")
        page.goto("https://lingos.pl/students", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        lesson_link = page.query_selector("a[href*='/learning/start'], a[href*='/learning/']")
        if lesson_link:
            start_href = lesson_link.get_attribute("href")
            page.goto("https://lingos.pl" + start_href if start_href.startswith("/") else start_href, wait_until="domcontentloaded")

    page.wait_for_timeout(3000)

    # 4. Pętla rozwiązywania słówek
    dictionary = {}
    solved_count = 0

    for step in range(50):
        content = page.content().lower()
        if any(term in content for term in ["koniec", "gratulacje", "podsumowanie", "brak słówek", "ukończono"]):
            print("[+] LEKCJA ZOSTAŁA W PEŁNI UKOŃCZONA I ZAPISANA!")
            break

        ans_input = page.query_selector("input[type='text']:not([readonly]):not([type='hidden'])")
        
        # Jeśli brak pola tekstowego, sprawdzamy czy trzeba kliknąć "Dalej" / "Następne"
        if not ans_input:
            next_btn = page.query_selector("button:has-text('Dalej'), a:has-text('Dalej'), input[value='Dalej']")
            if next_btn:
                next_btn.click(force=True)
                page.wait_for_timeout(2000)
                continue
            else:
                print("[!] Brak pola odpowiedzi oraz przycisku przejścia. Zamykanie...")
                break

        # Pobieranie słówka do przetłumaczenia
        word_el = page.query_selector(".word-to-translate, h3, strong, .word")
        word_text = word_el.inner_text().strip() if word_el else "słówko"

        answer = dictionary.get(word_text, "")
        
        ans_input.fill(answer)
        wait = random.randint(2, 4)
        print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Czekam {wait}s...")
        time.sleep(wait)

        # Wysyłanie odpowiedzi
        submit_btn = page.query_selector("button[type='submit'], input[type='submit']")
        if submit_btn:
            submit_btn.click(force=True)
        else:
            ans_input.press("Enter")

        page.wait_for_timeout(2500)

        # Zapamiętywanie poprawnej odpowiedzi w przypadku braku lub błędu
        correct_el = page.query_selector(".correct-answer, .alert-success, .translation-correct")
        if correct_el:
            correct_text = correct_el.inner_text().strip()
            dictionary[word_text] = correct_text
            print(f"    --> Zapamiętano poprawną odpowiedź: '{correct_text}'")

        solved_count += 1

    print(f"=== ZAKOŃCZONO. Łącznie przetworzonych kroków: {solved_count} ===")
    browser.close()
