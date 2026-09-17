import os
import sys
import time
import random
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

def accept_cookies_if_present(page):
    """Automatycznie zamyka/akceptuje wyskakujące banery z plikami cookies/RODO."""
    cookie_selectors = [
        "button:has-text('Akceptuj')",
        "button:has-text('Zgadzam się')",
        "button:has-text('Zezwól')",
        "button:has-text('Akceptuję')",
        "button:has-text('Accept')",
        "button:has-text('OK')",
        "#cookie-consent-accept",
        ".cookie-agree"
    ]
    for selector in cookie_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=1000):
                print(f"[+] Zamykanie baneru cookies ({selector})...")
                btn.click()
                page.wait_for_timeout(1000)
                break
        except Exception:
            pass

def run():
    if not USERNAME or not PASSWORD:
        print("[X] BŁĄD: Brak LINGOS_USER lub LINGOS_PASS w GitHub Secrets!")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        try:
            print("=== START BOT LINGOS ===")
            print("[1] Otwieranie strony logowania: https://lingos.pl/h/login ...")
            
            page.goto("https://lingos.pl/h/login", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Obsługa Cookies
            accept_cookies_if_present(page)
            page.screenshot(path="01_login_page.png")

            # Wprowadzanie danych logowania
            print("[2] Wprowadzanie danych logowania...")
            login_field = page.locator("input[name='login'], input[name='email'], input[name='username'], input[type='email'], input[type='text']").first
            login_field.wait_for(state="visible", timeout=10000)
            login_field.fill(USERNAME)

            pass_field = page.locator("input[name='password'], input[type='password']").first
            pass_field.fill(PASSWORD)

            page.screenshot(path="02_filled.png")

            print("[3] Klikanie przycisku Zaloguj...")
            submit_btn = page.locator("button[type='submit'], input[type='submit'], button:has-text('Zaloguj')").first
            submit_btn.click()

            page.wait_for_timeout(4000)
            accept_cookies_if_present(page)
            page.screenshot(path="03_after_login.png")

            # Weryfikacja zalogowania
            if "login" in page.url.lower():
                print("[X] BŁĄD LOGOWANIA: Odrzucono dane logowania lub strona przekierowała z powrotem do formularza!")
                page.screenshot(path="error.png")
                sys.exit(1)

            print(f"[OK] Zalogowano pomyślnie. Aktualny adres: {page.url}")

            # Szukanie przycisku do rozpoczęcia lekcji/sesji
            print("[4] Szukanie przycisku rozpoczęcia lekcji...")
            start_btn = page.locator("a:has-text('Lekcja'), button:has-text('Lekcja'), a:has-text('Rozpocznij'), button:has-text('Rozpocznij'), a:has-text('Start'), button:has-text('Start'), a[href*='learning']").first
            
            if start_btn.is_visible(timeout=5000):
                print("[+] Znaleziono przycisk lekcji! Przechodzenie do lekcji...")
                start_btn.click()
                page.wait_for_timeout(3000)
            else:
                print("[!] Brak bezpośredniego przycisku lekcji na stronie głównej, sprawdzam czy sesja trwa...")

            page.screenshot(path="04_session_start.png")

            # Rozwiązywanie lekcji
            print("[5] Rozpoczynanie wykonywania słówek...")
            solved_steps = 0
            
            for step in range(1, 35):
                # Symulacja naturalnego czasu reakcji człowieka (2 do 4 sekund)
                wait_time = random.uniform(2.0, 4.0)
                page.wait_for_timeout(int(wait_time * 1000))

                accept_cookies_if_present(page)

                # Wykrywanie końca lekcji
                body_text = page.inner_text("body").lower()
                if "koniec lekcji" in body_text or "gratulacje" in body_text or "podsumowanie" in body_text or "brak słówek" in body_text:
                    print("[+] Wykryto tekst końcowy – lekcja zakończona!")
                    break

                # Szukamy pola do wpisania odpowiedzi
                input_answer = page.locator("input[type='text']:not([readonly])").first
                
                if input_answer.is_visible(timeout=2000):
                    submit_answer = page.locator("button[type='submit'], button:has-text('Sprawdź'), button:has-text('Dalej')").first
                    if submit_answer.is_visible():
                        submit_answer.click()
                        solved_steps += 1
                        print(f"    Krok {step}: Zatwierdzono odpowiedź.")
                else:
                    # Jeśli brak pola tekstowego, szukamy przycisku przejścia dalej
                    next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej'), button:has-text('Kontynuuj')").first
                    if next_btn.is_visible(timeout=2000):
                        next_btn.click()
                        solved_steps += 1
                        print(f"    Krok {step}: Kliknięto Dalej.")
                    else:
                        print("    [i] Brak kolejnych pytań/przycisków – prawdopodobnie koniec sesji.")
                        break

            page.wait_for_timeout(2000)
            page.screenshot(path="05_finished.png")
            print(f"=== ZAKOŃCZONO SESJĘ (Wykonane kroki: {solved_steps}) ===")

        except Exception as e:
            print(f"[X] Wystąpił błąd podczas działania programu: {e}")
            page.screenshot(path="error.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
