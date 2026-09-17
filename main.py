import os
import sys
import time
import random
import re
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

def handle_cookies(page):
    cookie_selectors = [
        "#CybotCookiebotDialogBodyButtonAccept",
        "button:has-text('Akceptuj')",
        "button:has-text('Zgadzam się')",
        "button:has-text('Zezwól')"
    ]
    for sel in cookie_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=500):
                btn.click()
                page.wait_for_timeout(300)
                break
        except Exception:
            pass
            
    page.evaluate("""() => {
        const dialog = document.getElementById('CybotCookiebotDialog');
        if (dialog) dialog.remove();
        const overlay = document.getElementById('CybotCookiebotDialogBodyUnderlay');
        if (overlay) overlay.remove();
    }""")

def run():
    if not USERNAME or not PASSWORD:
        print("[X] BŁĄD: Brak danych logowania w GitHub Secrets!")
        sys.exit(1)

    dictionary = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        try:
            print("=== START BOT LINGOS ===")
            page.goto("https://lingos.pl/h/login", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            handle_cookies(page)

            print("Wpisywanie danych logowania...")
            page.fill("input[name='login'], input[name='email'], input[type='text']", USERNAME)
            page.fill("input[name='password'], input[type='password']", PASSWORD)
            page.click("button[type='submit'], input[type='submit']")
            page.wait_for_timeout(3000)

            if "login" in page.url.lower():
                print("[X] BŁĄD LOGOWANIA: Sprawdź login i hasło w Secrets!")
                sys.exit(1)

            print("[OK] Zalogowano pomyślnie!")

            # Wejście na kokpit i kliknięcie zielonego przycisku "Ucz się"
            print("Szukam przycisku 'Ucz się' na kokpicie...")
            page.goto("https://lingos.pl/", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            handle_cookies(page)

            # Próba kliknięcia w zielony przycisk nauki
            learn_btn = page.locator("a:has-text('Ucz się'), button:has-text('Ucz się'), a.btn-success, a.btn-primary").first
            if learn_btn.is_visible(timeout=4000):
                learn_btn.click()
                print("[OK] Kliknięto przycisk rozpoczęcia nauki!")
                page.wait_for_timeout(3000)
            else:
                print("[!] Nie znaleziono przycisku na kokpicie, wchodzę bezpośrednio pod adres lekcji...")
                page.goto("https://lingos.pl/students/group", wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(2000)

            solved_steps = 0

            for step in range(1, 80):
                time.sleep(random.uniform(1.8, 2.8))
                handle_cookies(page)

                body_text = page.inner_text("body").lower()
                if any(w in body_text for w in ["koniec", "gratulacje", "podsumowanie", "ukończono", "brak słówek"]):
                    print("[+] Lekcja została w pełni ukończona!")
                    break

                # Pobieranie słówka
                word_el = page.locator("h3, .word-title, div:has-text('PRZETŁUMACZ') + div, .word-to-translate").first
                current_word = ""
                if word_el.is_visible(timeout=500):
                    raw_word = word_el.inner_text().strip()
                    current_word = raw_word.replace("PRZETŁUMACZ", "").strip()

                # Pole odpowiedzi
                input_answer = page.locator("input[placeholder*='odpowiedź'], input[placeholder*='Odpowiedź'], input[type='text']:not([readonly])").first

                if input_answer.is_visible(timeout=1000):
                    answer_to_type = dictionary.get(current_word, "a")
                    
                    input_answer.fill("")
                    input_answer.fill(answer_to_type)
                    page.wait_for_timeout(300)
                    input_answer.press("Enter")
                    solved_steps += 1
                    print(f"[{step}] Słówko: '{current_word}' -> Wpisano: '{answer_to_type}'")
                    page.wait_for_timeout(1200)

                # Obsługa błędów / przycisku Dalej
                next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej')").first
                if next_btn.is_visible(timeout=1000):
                    correct_box = page.locator(".border-red-500, .bg-red-100, .alert-danger, div:has-text('BŁĘDNA')").first
                    if correct_box.is_visible(timeout=300):
                        box_text = correct_box.inner_text().strip()
                        lines = [line.strip() for line in box_text.split('\n') if line.strip()]
                        clean_ans = lines[-1] if lines else box_text
                        clean_ans = re.sub(r'^(BŁĘDNA ODPOWIEDŹ|PRZETŁUMACZ)', '', clean_ans, flags=re.IGNORECASE).strip()
                        
                        if current_word and clean_ans and clean_ans != "a":
                            dictionary[current_word] = clean_ans
                            print(f"    [+] Zapamiętano poprawną odpowiedź: '{current_word}' = '{clean_ans}'")

                    next_btn.click()
                    print(f"[{step}] Kliknięto 'Dalej'.")
                else:
                    page.keyboard.press("Enter")

            print(f"=== ZAKOŃCZONO SUKCESEM (Wykonane kroki: {solved_steps}) ===")
            page.screenshot(path="sukces.png")

        except Exception as e:
            print(f"[X] Błąd krytyczny: {e}")
            page.screenshot(path="error.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
