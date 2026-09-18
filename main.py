import os
import sys
import time
import random
import re
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

def handle_cookies(page):
    try:
        page.evaluate("""() => {
            const dialog = document.getElementById('CybotCookiebotDialog');
            if (dialog) dialog.remove();
            const overlay = document.getElementById('CybotCookiebotDialogBodyUnderlay');
            if (overlay) overlay.remove();
        }""")
    except Exception:
        pass

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

            # Bezpośrednie wejście w lekcję grupy ze zdjęcia (groupId=19788)
            target_url = "https://lingos.pl/learning/start/0?groupId=19788"
            print(f"Wchodzę bezpośrednio w lekcję: {target_url}")
            page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            handle_cookies(page)

            solved_steps = 0

            # Główna pętla przerabiania słówek
            for step in range(1, 120):
                time.sleep(random.uniform(1.5, 2.5))
                handle_cookies(page)

                body_text = page.inner_text("body").lower()
                if any(w in body_text for w in ["gratulacje", "podsumowanie", "ukończono", "brak słówek do powtórki", "koniec"]):
                    print("[+] Lekcja została w pełni ukończona!")
                    break

                # Pobieranie słówka do przetłumaczenia
                word_el = page.locator("h3, .word-title, div.word-to-translate, .card-title, label, .text-center h4").first
                current_word = ""
                if word_el.is_visible(timeout=1000):
                    current_word = word_el.inner_text().strip()

                # Pole do wpisania odpowiedzi
                input_answer = page.locator("input[placeholder*='odpowiedź'], input[placeholder*='Odpowiedź'], input[type='text']:not([readonly])").first

                if input_answer.is_visible(timeout=1500) and current_word:
                    answer_to_type = dictionary.get(current_word, "a")
                    
                    input_answer.fill("")
                    input_answer.fill(answer_to_type)
                    page.wait_for_timeout(300)
                    input_answer.press("Enter")
                    solved_steps += 1
                    print(f"[{step}] Słówko: '{current_word}' -> Wpisano: '{answer_to_type}'")
                    page.wait_for_timeout(1500)

                # Przycisk Dalej / zatwierdzenia odpowiedzi
                next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej'), button:has-text('Sprawdź')").first
                if next_btn.is_visible(timeout=1000):
                    # Sprawdzamy czy wyrzuciło błąd i podświetliło poprawną odpowiedź
                    correct_box = page.locator(".alert-danger, .text-danger, .correct-answer, .bg-red-100, .border-red-500, span.text-success").first
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
