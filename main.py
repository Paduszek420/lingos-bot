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
            if btn.is_visible(timeout=500):
                btn.click()
                page.wait_for_timeout(500)
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

            # Szukanie i klikanie przycisku startu lekcji
            print("[2] Otwieranie lekcji...")
            start_btn = page.locator("a:has-text('Lekcja'), button:has-text('Lekcja'), a:has-text('Rozpocznij'), button:has-text('Rozpocznij'), a:has-text('Start'), button:has-text('Start'), a[href*='learning']").first
            if start_btn.is_visible(timeout=5000):
                start_btn.click()
                page.wait_for_timeout(3000)

            # Główna pętla rozwiązywania powtórek
            print("[3] Rozpoczynam odpowiadanie na słówka w lekcji...")
            solved_steps = 0

            for step in range(1, 40):
                # Symulacja naturalnego odstępu czasowego (2 do 4 sekund)
                wait_time = random.uniform(2.0, 4.0)
                page.wait_for_timeout(int(wait_time * 1000))
                accept_cookies_if_present(page)

                # Sprawdzenie czy nie nastąpił koniec lekcji
                body_text = page.inner_text("body").lower()
                if "koniec lekcji" in body_text or "gratulacje" in body_text or "ukończono" in body_text or "podsumowanie" in body_text:
                    print("[+] Wykryto podsumowanie / koniec lekcji!")
                    break

                # 1. Szukamy pola tekstowego z wpisywaniem odpowiedzi
                input_answer = page.locator("input[placeholder*='odpowiedź'], input[placeholder*='Odpowiedź'], input[type='text']:not([readonly])").first

                if input_answer.is_visible(timeout=2500):
                    # Wprowadzamy odpowiedź (np. "test" lub cokolwiek, jeśli nie znamy słówka)
                    input_answer.fill("a")
                    page.wait_for_timeout(500)
                    
                    # Wciśnięcie Enter w polu odpowiedzi
                    input_answer.press("Enter")
                    solved_steps += 1
                    print(f"    Krok {step}: Wpisano odpowiedź i naciśnięto Enter.")
                    
                    # Sprawdzamy czy trzeba kliknąć przycisk zatwierdzenia jeśli Enter nie zadziałał
                    check_btn = page.locator("button:has-text('Sprawdź'), button:has-text('Wyślij'), button[type='submit']").first
                    if check_btn.is_visible(timeout=1000):
                        check_btn.click()
                else:
                    # 2. Szukamy przycisku przejścia do następnego słówka ("Dalej" / "Kontynuuj")
                    next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej'), button:has-text('Kontynuuj'), button:has-text('Następne')").first
                    if next_btn.is_visible(timeout=2000):
                        next_btn.click()
                        solved_steps += 1
                        print(f"    Krok {step}: Kliknięto przycisk 'Dalej'.")
                    else:
                        # Jeśli ani pole tekstowe ani 'Dalej' nie są widoczne, próbujemy nacisnąć Enter ogólnie
                        page.keyboard.press("Enter")
                        print(f"    Krok {step}: Brak widocznych przycisków, wysłano zdarzenie Enter.")

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
