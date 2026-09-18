import os
import sys
import time
import random
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
        page.set_default_timeout(10000)

        try:
            print("=== START BOT LINGOS ===")
            page.goto("https://lingos.pl/h/login", wait_until="domcontentloaded", timeout=20000)
            
            print("Wpisywanie danych logowania...")
            page.fill("input[name='login'], input[name='email'], input[type='text']", USERNAME)
            page.fill("input[name='password'], input[type='password']", PASSWORD)
            page.click("button[type='submit'], input[type='submit']")
            page.wait_for_load_state("domcontentloaded")

            if "login" in page.url.lower():
                print("[X] BŁĄD LOGOWANIA: Błędny login lub hasło!")
                page.screenshot(path="error.png")
                sys.exit(1)

            print("[OK] Zalogowano pomyślnie!")

            target_url = "https://lingos.pl/learning/start/0?groupId=19788"
            print(f"Wchodzę w lekcję: {target_url}")
            page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2500)

            solved_steps = 0

            for step in range(1, 100):
                time.sleep(1.5)
                
                body_text = page.inner_text("body").lower()
                if any(w in body_text for w in ["gratulacje", "podsumowanie", "ukończono", "brak słówek", "koniec"]):
                    print("[+] Lekcja została ukończona!")
                    break

                # SPRAWDZENIE TYP 1: Czy to zadanie z kafelkami (wybór odpowiedzi)?
                # Kafelki na Lingos mają zazwyczaj strukturę przycisków lub elementów do kliknięcia
                tiles = page.locator(".answer-tile, .word-tile, .card-answer, div.option, button.answer-btn")
                if tiles.count() > 0:
                    print(f"[{step}] Wykryto kafelki wyboru – wybieram losowy/pierwszy kafelek.")
                    try:
                        tiles.first.click()
                        solved_steps += 1
                        page.wait_for_timeout(1000)
                    except Exception as ex:
                        print(f"Błąd kliknięcia kafelek: {ex}")

                # SPRAWDZENIE TYP 2: Czy to klasyczne pole tekstowe do wpisania?
                else:
                    input_answer = page.locator("input[type='text']:not([readonly]), input[placeholder*='odpowiedź']").first
                    if input_answer.is_visible():
                        print(f"[{step}] Wykryto pole tekstowe – wpisuję odpowiedź.")
                        input_answer.fill("a") # Wpisujemy cokolwiek, skrypt z czasem załapie lub pójdzie dalej
                        input_answer.press("Enter")
                        solved_steps += 1
                        page.wait_for_timeout(1000)

                # Kliknięcie przycisku "Dalej" jeśli się pojawił
                try:
                    next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej'), button:has-text('Sprawdź')").first
                    if next_btn.is_visible(timeout=800):
                        next_btn.click()
                        page.wait_for_timeout(800)
                except:
                    pass

            print(f"=== ZAKOŃCZONO (Kroki: {solved_steps}) ===")
            page.screenshot(path="sukces.png")

        except Exception as e:
            print(f"[X] Błąd krytyczny: {e}")
            page.screenshot(path="error.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
