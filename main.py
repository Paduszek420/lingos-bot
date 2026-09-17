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

            print("Szukam przycisku 'Ucz się' na kokpicie...")
            page.goto("https://lingos.pl/", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            handle_cookies(page)

            # Kliknięcie w naukę i dłuższe czekanie, żeby załadował się panel słówek
            learn_btn = page.locator("a:has-text('Ucz się'), button:has-text('Ucz się'), a.btn-success, a.btn-primary").first
            if learn_btn.is_visible(timeout=4000):
                learn_btn.click()
                print("[OK] Kliknięto przycisk rozpoczęcia nauki!")
                page.wait_for_timeout(4000) # Czekamy aż wejdzie w sesję
            else:
                print("[!] Nie znaleziono przycisku, wchodzę pod adres grup...")
                page.goto("https://lingos.pl/students/group", wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(3000)

            # Jeśli jest jeszcze jakiś wewnętrzny przycisk startu zestawu w grupie - kliknij go
            start_set_btn = page.locator("a:has-text('Rozpocznij'), button:has-text('Rozpocznij'), a:has-text('Ćwicz'), .start-lesson").first
            if start_set_btn.is_visible(timeout=2000):
                start_set_btn.click()
                print("[OK] Kliknięto start zestawu słówek!")
                page.wait_for_timeout(3000)

            solved_steps = 0

            # Właściwa pętla rozwiązywania
            for step in range(1, 80):
                time.sleep(random.uniform(1.5, 2.5))
                handle_cookies(page)

                body_text = page.inner_text("body").lower()
                if any(w in body_text for w in ["gratulacje", "podsumowanie", "ukończono", "brak słówek do powtórki"]):
                    print("[+] Lekcja została w pełni ukończona!")
                    break

                # Szukamy słówka do przetłumaczenia
                word_el = page.locator("h3, .word-title, div.word-to-translate, .card-title, label").first
                current_word = ""
                if word_el.is_visible(timeout=1000):
                    current_word = word_el.inner_text().strip()

                # Szukamy pola tekstowego na odpowiedź
                input_answer = page.locator("input[placeholder*='odpowiedź'], input[placeholder*='Odpowiedź'], input[type='text']:not([readonly])").first

                if input_answer.is_visible(timeout=1500) and current_word:
                    # Bierzemy zapamiętaną odpowiedź lub wpisujemy domyślną, jeśli nie znamy
                    answer_to_type = dictionary.get(current_word, "a")
                    
                    input_answer.fill("")
                    input_answer.fill(answer_to_type)
                    page.wait_for_timeout(300)
                    input_answer.press("Enter")
                    solved_steps += 1
                    print(f"[{step}] Słówko: '{current_word}' -> Wpisano: '{answer_to_type}'")
                    page.wait_for_timeout(1500)

                # Sprawdzamy przycisk Dalej / zatwierdzenia
                next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej'), button:has-text('Sprawdź')").first
                if next_btn.is_visible(timeout=1000):
                    # Jeśli odpowiedź była zła, wyciągnij poprawną z czerwonego/zielonego boxa
                    correct_box = page.locator(".alert-danger, .text-danger, .correct-answer, .bg-red-100, .border-red-500").first
                    if correct_box.is_visible(timeout=300):
                        box_text = correct_box.inner_text().strip()
                        lines = [l.strip() for l in box_text.split('\n') if l.strip()]
                        clean_ans = lines[-1] if lines else box_text
                        clean_ans = re.sub(r'^(BŁĘDNA ODPOWIEDŹ|Prawidłowa odpowiedź:)', '', clean_ans, flags=re.IGNORECASE).strip()
                        
                        if current_word and clean_ans and clean_ans != "a":
                            dictionary[current_word] = clean_ans
                            print(f"    [+] Zapamiętano poprawną odpowiedź: '{current_word}' = '{clean_ans}'")

                    next_btn.click()
                    page.wait_for_timeout(1000)
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
