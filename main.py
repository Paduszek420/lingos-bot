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
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        try:
            print("=== START SESJI LINGOS ===")
            page.goto("https://lingos.pl/h/login", wait_until="domcontentloaded")
            time.sleep(2)

            # BRUTALNE USUNIĘCIE CIASTECZEK Z DOM (żeby w ogóle nie istniały na ekranie)
            try:
                page.evaluate("document.getElementById('CybotCookiebotDialog')?.remove();")
                page.evaluate("document.querySelector('.cybot-cookiebot')?.remove();")
                print("Usunięto baner ciasteczek ze strony.")
            except:
                pass

            # Wpisanie loginu i hasła
            print("Wpisuję dane logowania...")
            login_input = page.locator("input[type='email'], input[type='text'], input[placeholder*='Email']").first
            login_input.wait_for(state="visible", timeout=15000)
            login_input.fill(USERNAME)
            
            pass_input = page.locator("input[type='password']").first
            pass_input.fill(PASSWORD)
            
            submit_btn = page.locator("button:has-text('Zaloguj się'), button[type='submit']").first
            submit_btn.click()
            
            print("Czekam na zalogowanie...")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # Przejście do lekcji
            target_url = "https://lingos.pl/learning/start/0?groupId=19788"
            print(f"Otwieram lekcję: {target_url}")
            page.goto(target_url, wait_until="domcontentloaded")
            time.sleep(3)

            # Pętla wykonująca słówka
            solved = 0
            for i in range(1, 120):
                content = page.inner_text("body").lower()
                
                if any(kw in content for kw in ["gratulacje", "podsumowanie", "ukończono", "lekcja wykonana", "dzisiaj powtórzone"]):
                    print("[+] Sesja zakończona sukcesem! Słówka zrobione.")
                    break

                # Klikanie odpowiedzi (kafelki)
                options = page.locator(".answer-tile, .word-tile, div.option, button.answer-btn, .answer")
                if options.count() > 0:
                    options.first.click()
                    solved += 1
                    time.sleep(1.2)
                else:
                    # Pole tekstowe
                    text_input = page.locator("input[type='text']:not([readonly])")
                    if text_input.count() > 0:
                        text_input.first.fill("auto")
                        text_input.first.press("Enter")
                        solved += 1
                        time.sleep(1.2)

                # Przycisk Dalej
                try:
                    next_btn = page.locator("button:has-text('Dalej'), button:has-text('Sprawdź'), a:has-text('Dalej')")
                    if next_btn.count() > 0:
                        next_btn.first.click()
                        time.sleep(0.8)
                except:
                    pass

            print(f"=== ZROBIONE! Przerobiono elementów: {solved} ===")

        except Exception as e:
            print(f"[X] Wystąpił błąd podczas sesji: {e}")
            page.screenshot(path="error_final.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
