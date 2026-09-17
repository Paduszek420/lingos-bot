import os
import sys
import time
import random
import re
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

def accept_cookies_if_present(page):
    cookie_selectors = [
        "button:has-text('Akceptuj')",
        "button:has-text('Zgadzam się')",
        "button:has-text('Zezwól')",
        "button:has-text('Akceptuję')"
    ]
    for selector in cookie_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=200):
                btn.click()
                page.wait_for_timeout(200)
                break
        except Exception:
            pass

def run():
    if not USERNAME or not PASSWORD:
        print("[X] BŁĄD: Brak danych w Secrets!")
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
            accept_cookies_if_present(page)

            # Logowanie
            login_field = page.locator("input[name='login'], input[name='email'], input[type='text']").first
            login_field.fill(USERNAME)

            pass_field = page.locator("input[name='password'], input[type='password']").first
            pass_field.fill(PASSWORD)

            page.locator("button[type='submit'], input[type='submit']").first.click()
            page.wait_for_timeout(2500)

            if "login" in page.url.lower():
                print("[X] BŁĄD LOGOWANIA!")
                sys.exit(1)

            print("[OK] Zalogowano! Otwieranie lekcji...")

            # Uruchomienie lekcji
            start_btn = page.locator("a:has-text('Lekcja'), button:has-text('Lekcja'), a:has-text('Rozpocznij'), button:has-text('Start')").first
            if start_btn.is_visible(timeout=4000):
                start_btn.click()
                page.wait_for_timeout(2500)

            solved_steps = 0

            for step in range(1, 50):
                wait_time = random.uniform(2.0, 3.5)
                page.wait_for_timeout(int(wait_time * 1000))
                accept_cookies_if_present(page)

                body_text = page.inner_text("body").lower()
                if "koniec" in body_text or "gratulacje" in body_text or "podsumowanie" in body_text:
                    print("[+] Wykryto koniec lekcji!")
                    break

                # Wyciąganie nazwy polskiego słówka (np. odpaść, wycofać się)
                word_el = page.locator("h3, .word-title, div:has-text('PRZETŁUMACZ') + div").first
                current_word = ""
                if word_el.is_visible(timeout=500):
                    raw_word = word_el.inner_text().strip()
                    # Czyszczenie z nagłówków
                    current_word = raw_word.replace("PRZETŁUMACZ", "").strip()

                # 1. Sprawdzamy czy widoczne jest pole odpowiedzi
                input_answer = page.locator("input[placeholder*='odpowiedź'], input[placeholder*='Odpowiedź']").first

                if input_answer.is_visible(timeout=1500):
                    # Pobieramy zapamiętaną odpowiedź ze słownika
                    answer_to_type = dictionary.get(current_word, "a")
                    
                    input_answer.fill(answer_to_type)
                    page.wait_for_timeout(300)
                    input_answer.press("Enter")
                    solved_steps += 1
                    print(f"[{step}] Słówko: '{current_word}' -> Odpowiedź: '{answer_to_type}'")
                    page.wait_for_timeout(1000)

                # 2. Sprawdzamy czy jest ekran z błędną odpowiedzią i przyciskiem "Dalej [Enter]"
                next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej')").first
                
                if next_btn.is_visible(timeout=1500):
                    # Pobieranie poprawnej odpowiedzi wyłącznie z czerwonej ramki
                    correct_box = page.locator(".border-red-500, .bg-red-100, div:has-text('drop out')").first
                    if correct_box.is_visible(timeout=500):
                        box_text = correct_box.inner_text().strip()
                        # Wyciąganie czystego tekstu (odrzucenie 'BŁĘDNA ODPOWIEDŹ')
                        lines = [line.strip() for line in box_text.split('\n') if line.strip()]
                        clean_ans = lines[-1] if lines else box_text
                        clean_ans = re.sub(r'^(BŁĘDNA ODPOWIEDŹ|PRZETŁUMACZ)', '', clean_ans, flags=re.IGNORECASE).strip()
                        
                        if current_word and clean_ans and clean_ans != "a":
                            dictionary[current_word] = clean_ans
                            print(f"    [+] Zapamiętano do słownika: '{current_word}' = '{clean_ans}'")

                    next_btn.click()
                    print(f"[{step}] Kliknięto 'Dalej'.")
                else:
                    page.keyboard.press("Enter")

            page.wait_for_timeout(2000)
            page.screenshot(path="05_finished.png")
            print(f"=== ZAKOŃCZONO (Wykonane kroki: {solved_steps}) ===")

        except Exception as e:
            print(f"[X] Błąd: {e}")
            page.screenshot(path="error.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
