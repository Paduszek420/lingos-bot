import os
import time
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

def run():
    if not USERNAME or not PASSWORD:
        print("[X] BRAK DANYCH: Nie znaleziono LINGOS_USER lub LINGOS_PASS w GitHub Secrets!")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        try:
            print("=== START BOT LINGOS ===")
            print("Otwieranie bezpośredniego linku do logowania: https://lingos.pl/h/login ...")
            
            # Wchodzimy bezpośrednio na formularz logowania
            page.goto("https://lingos.pl/h/login", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            page.screenshot(path="01_login_page.png")

            print("Wprowadzanie danych logowania...")
            
            # Wyszukiwanie pola loginu/emaila
            login_field = page.locator("input[name='login'], input[name='email'], input[name='username'], input[type='email'], input[type='text']").first
            login_field.wait_for(state="visible", timeout=10000)
            login_field.fill(USERNAME)

            # Wyszukiwanie pola hasła
            pass_field = page.locator("input[name='password'], input[type='password']").first
            pass_field.fill(PASSWORD)

            page.screenshot(path="02_filled.png")

            print("Klikanie przycisku Zaloguj...")
            submit_btn = page.locator("button[type='submit'], input[type='submit'], button:has-text('Zaloguj')").first
            submit_btn.click()

            page.wait_for_timeout(4000)
            page.screenshot(path="03_after_login.png")
            print(f"Zalogowano! Aktualna strona: {page.url}")

            # Wykrywanie przycisku rozpoczęcia lekcji/sesji
            print("Szukanie przycisku rozpoczęcia lekcji...")
            start_btn = page.locator("a:has-text('Lekcja'), button:has-text('Lekcja'), a:has-text('Rozpocznij'), button:has-text('Rozpocznij'), a:has-text('Start'), button:has-text('Start')").first
            
            if start_btn.is_visible(timeout=5000):
                print("Znaleziono przycisk lekcji! Klikam...")
                start_btn.click()
                page.wait_for_timeout(3000)
            else:
                print("Nie znaleziono przycisku startu lub sesja jest już w trakcie/zrobiona.")

            page.screenshot(path="04_session.png")

            # Pętla wykonująca powtórki (maksymalnie 30 kroków)
            print("Rozpoczynanie wykonywania słówek...")
            for step in range(1, 31):
                page.wait_for_timeout(1500) # Naturalne opóźnienie 1.5 sekundy
                
                # Szukamy czy jest pole do wpisania odpowiedzi lub przycisk dalej
                input_answer = page.locator("input[type='text']:not([readonly])").first
                
                if input_answer.is_visible(timeout=2000):
                    # Tutaj bot wpisuje cokolwiek lub zatwierdza
                    submit_answer = page.locator("button[type='submit'], button:has-text('Sprawdź'), button:has-text('Dalej')").first
                    if submit_answer.is_visible():
                        submit_answer.click()
                        print(f"Krok {step}: Wysłano odpowiedź.")
                else:
                    # Szukamy ogólnego przycisku przejścia dalej
                    next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej'), button:has-text('Kontynuuj')").first
                    if next_btn.is_visible(timeout=2000):
                        next_btn.click()
                        print(f"Krok {step}: Kliknięto Dalej.")
                    else:
                        print("Brak kolejnych pytań - prawdopodobnie koniec sesji na dziś.")
                        break

            page.wait_for_timeout(2000)
            page.screenshot(path="05_finished.png")
            print("=== ZAKOŃCZONO SESJĘ EFEKTYWNIE ===")

        except Exception as e:
            print(f"[X] Wystąpił błąd podczas działania programu: {e}")
            page.screenshot(path="error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
