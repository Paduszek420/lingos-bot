import os
import sys
import time
import random
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

def accept_cookies_if_present(page):
    """Zamykanie wyskakujących banerów RODO / Cookies."""
    cookie_selectors = [
        "button:has-text('Akceptuj')",
        "button:has-text('Zgadzam się')",
        "button:has-text('Zezwól')",
        "button:has-text('Akceptuję')",
        "button:has-text('Accept')",
        "button:has-text('OK')"
    ]
    for selector in cookie_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=300):
                btn.click()
                page.wait_for_timeout(300)
                break
        except Exception:
            pass

def run():
    if not USERNAME or not PASSWORD:
        print("[X] BŁĄD: Brak LINGOS_USER lub LINGOS_PASS w GitHub Secrets!")
        sys.exit(1)

    # Słownik dynamicznie zapamiętujący poprawne odpowiedzi
    dictionary = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        try:
            print("=== START BOT LINGOS ===")
            print("[1] Logowanie na https://lingos.pl/h/login ...")
            
            page.goto("https://lingos.pl/h/login", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            accept_cookies_if_present(page)

            # Logowanie
            login_field = page.locator("input[name='login'], input[name='email'], input[type='email'], input[type='text']").first
            login_field.wait_for(state="visible", timeout=10000)
            login_field.fill(USERNAME)

            pass_field = page.locator("input[name='password'], input[type='password']").first
            pass_field.fill(PASSWORD)

            submit_btn = page.locator("button[type='submit'], input[type='submit'], button:has-text('Zaloguj')").first
            submit_btn.click()

            page.wait_for_timeout(3000)
            accept_cookies_if_present(page)

            if "login" in page.url.lower():
                print("[X] BŁĄD LOGOWANIA: Odrzucono dane logowania!")
                page.screenshot(path="error.png")
                sys.exit(1)

            print(f"[OK] Zalogowano pomyślnie. Strona: {page.url}")

            # Otwieranie lekcji
            print("[2] Otwieranie lekcji...")
            start_btn = page.locator("a:has-text('Lekcja'), button:has-text('Lekcja'), a:has-text('Rozpocznij'), button:has-text('Rozpocznij'), a:has-text('Start'), button:has-text('Start'), a[href*='learning']").first
            if start_btn.is_visible(timeout=5000):
                start_btn.click()
                page.wait_for_timeout(3000)

            print("[3] Rozpoczynam rozwiązywanie lekcji...")
            solved_steps = 0

            for step in range(1, 45):
                # Symulacja naturalnego opóźnienia czlowieka (2-4 sekundy)
                wait_time = random.uniform(2.0, 4.0)
                page.wait_for_timeout(int(wait_time * 1000))
                accept_cookies_if_present(page)

                # Wykrywanie końca lekcji
                body_text = page.inner_text("body").lower()
                if "koniec lekcji" in body_text or "gratulacje" in body_text or "ukończono" in body_text or "podsumowanie" in body_text:
                    print("[+] Wykryto koniec lekcji!")
                    break

                # Pobranie słówka do przetłumaczenia (np. "odpaść, wycofać się")
                word_element = page.locator("h1, h2, h3, div:has-text('PRZETŁUMACZ') + div, .word-title").first
                current_word = word_element.inner_text().strip() if word_element.is_visible() else ""

                # 1. Szukamy pola wpisywania odpowiedzi
                input_answer = page.locator("input[placeholder*='odpowiedź'], input[placeholder*='Odpowiedź'], input[type='text']:not([readonly])").first

                if input_answer.is_visible(timeout=2000):
                    # Sprawdzamy czy mamy już to słówko w pamięci słownika
                    answer_to_type = dictionary.get(current_word, "a")
                    
                    input_answer.fill(answer_to_type)
                    page.wait_for_timeout(300)
                    input_answer.press("Enter")
                    solved_steps += 1
                    print(f"    Krok {step}: Wpisano '{answer_to_type}' dla słówka '{current_word}'.")
                    page.wait_for_timeout(1000)

                # 2. Odczytanie poprawnej odpowiedzi (jeśli poprzednia była błędna) i kliknięcie "Dalej [Enter]"
                next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej'), button:has-text('Enter')").first
                
                if next_btn.is_visible(timeout=2000):
                    # Jeśli widoczny jest napis o błędnej odpowiedzi, pobieramy poprawną treść do słownika
                    correct_ans_box = page.locator(".bg-red-100, .border-red-500, div:has-text('BŁĘDNA ODPOWIEDŹ')").first
                    if correct_ans_box.is_visible():
                        correct_text = correct_ans_box.inner_text().strip()
                        if current_word and correct_text:
                            # Czyszczenie tekstu z niepotrzebnych fraz
                            clean_ans = correct_text.replace("BŁĘDNA ODPOWIEDŹ", "").strip()
                            dictionary[current_word] = clean_ans
                            print(f"    [+] Zapamiętano poprawną odpowiedź: '{current_word}' -> '{clean_ans}'")

                    next_btn.click()
                    print(f"    Krok {step}: Kliknięto 'Dalej [Enter]'.")
                else:
                    # Alternatywne zatwierdzenie klawiszem Enter
                    page.keyboard.press("Enter")

            page.wait_for_timeout(2000)
            page.screenshot(path="05_finished.png")
            print(f"=== ZAKOŃCZONO SESJĘ (Wykonane kroki: {solved_steps}) ===")

        except Exception as e:
            print(f"[X] Wystąpił błąd: {e}")
            page.screenshot(path="error.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
