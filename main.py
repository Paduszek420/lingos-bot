import os
import sys
import time
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

def run():
    if not USERNAME or not PASSWORD:
        print("[X] BŁĄD: Brak danych logowania w GitHub Secrets!")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        try:
            print("=== START BOT LINGOS ===")
            page.goto("https://lingos.pl/h/login", wait_until="networkidle")
            
            # KLUCZOWY KROK: Zamknięcie banera cookies z drugiego zdjęcia
            try:
                print("Szukam banera cookies...")
                # Przycisk "Zezwól na wszystkie" lub "Zezwól" w okienku Cookiebot
                cookie_btn = page.locator("button:has-text('Zezwól na wszystkie'), button:has-text('Zezwól'), #CybotCookiebotDialogBodyButtonAccept")
                if cookie_btn.count() > 0:
                    cookie_btn.first.click()
                    print("Zamknięto okienko ciasteczek.")
                    time.sleep(1)
            except Exception as e:
                print(f"Nie znaleziono ciasteczek lub pominięto: {e}")

            print("Wpisywanie danych logowania...")
            page.wait_for_selector("input[name='login']", timeout=10000)
            page.fill("input[name='login']", USERNAME)
            page.fill("input[name='password']", PASSWORD)
            
            # Kliknięcie przycisku logowania
            page.click("button[type='submit'], input[type='submit']")
            page.wait_for_load_state("networkidle")

            print("[OK] Zalogowano pomyślnie!")

            target_url = "https://lingos.pl/learning/start/0?groupId=19788"
            print(f"Wchodzę w lekcję: {target_url}")
            page.goto(target_url, wait_until="networkidle")
            time.sleep(2)

            solved_steps = 0

            for step in range(1, 100):
                body_text = page.inner_text("body").lower()
                if any(w in body_text for w in ["gratulacje", "podsumowanie", "ukończono", "brak słówek", "koniec", "lekcja wykonana", "dzisiaj powtórzone"]):
                    print("[+] Lekcja została ukończona!")
                    break

                # Sprawdzenie kafelków odpowiedzi
                tiles = page.locator(".answer-tile, .word-tile, .card-answer, div.option, button.answer-btn")
                if tiles.count() > 0:
                    print(f"[{step}] Klikam kafelek odpowiedzi.")
                    tiles.first.click()
                    solved_steps += 1
                    time.sleep(1.5)
                else:
                    # Sprawdzenie pola tekstowego
                    input_answer = page.locator("input[type='text']:not([readonly])")
                    if input_answer.count() > 0:
                        print(f"[{step}] Wpisuję odpowiedź.")
                        input_answer.first.fill("a")
                        input_answer.first.press("Enter")
                        solved_steps += 1
                        time.sleep(1.5)

                # Kliknięcie Dalej / Sprawdź
                try:
                    next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej'), button:has-text('Sprawdź')")
                    if next_btn.count() > 0:
                        next_btn.first.click()
                        time.sleep(1)
                except:
                    pass

            print(f"=== ZAKOŃCZONO SUKCESEM (Kroki: {solved_steps}) ===")

        except Exception as e:
            print(f"[X] Błąd: {e}")
            page.screenshot(path="error.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
