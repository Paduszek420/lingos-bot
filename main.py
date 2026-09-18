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

            # Usunięcie baneru ciasteczek
            try:
                page.evaluate("document.getElementById('CybotCookiebotDialog')?.remove();")
                page.evaluate("document.querySelector('.cybot-cookiebot')?.remove();")
            except:
                pass

            # Logowanie
            print("Wpisuję dane logowania...")
            page.locator("input[type='email'], input[type='text'], input[placeholder*='Email']").first.fill(USERNAME)
            page.locator("input[type='password']").first.fill(PASSWORD)
            page.locator("button:has-text('Zaloguj się'), button[type='submit']").first.click()
            
            print("Czekam na zalogowanie...")
            page.wait_for_load_state("networkidle")
            time.sleep(4)

            # Kliknięcie przycisku "Ucz się"
            print("Szukam przycisku 'Ucz się'...")
            try:
                learn_btn = page.locator("button:has-text('Ucz się'), a:has-text('Ucz się')").first
                if learn_btn.is_visible(timeout=5000):
                    learn_btn.click()
                    print("Kliknięto 'Ucz się'!")
                    time.sleep(4)
                else:
                    page.goto("https://lingos.pl/learning", wait_until="domcontentloaded")
                    time.sleep(4)
            except:
                page.goto("https://lingos.pl/learning", wait_until="domcontentloaded")
                time.sleep(4)

            # Pętla do rozwiązywania słówek
            print("Rozpoczynam rozwiązywanie słówek...")
            for i in range(1, 100):
                content = page.inner_text("body").lower()
                
                if any(kw in content for kw in ["gratulacje", "podsumowanie", "ukończono", "lekcja wykonana", "dzisiaj powtórzone"]):
                    print("[+] Lekcja zrobiona w 100%!")
                    break

                # Obsługa pól tekstowych (wpisywanie odpowiedzi)
                text_input = page.locator("input[type='text']:not([readonly])")
                if text_input.count() > 0:
                    try:
                        # Próba odczytania podpowiedzi / słówka do przetłumaczenia ze strony
                        # Jeśli Lingos ma opcję "pokaż odpowiedź" lub podpowiedź, klikamy ją
                        hint_btn = page.locator("button:has-text('Podpowiedź'), a:has-text('Podpowiedź'), .icon-help, text='Przetłumacz'")
                        if hint_btn.count() > 0:
                            hint_btn.first.click()
                            time.sleep(0.5)
                        
                        # Wpisujemy cokolwiek lub spację / encję, a potem klikamy Dalej, lub próbujemy przejść dalej
                        text_input.first.fill("skip")
                        text_input.first.press("Enter")
                    except:
                        pass

                # Obsługa kafelków / wielokrotnego wyboru
                options = page.locator(".answer-tile, .word-tile, div.option, button.answer-btn")
                if options.count() > 0:
                    try:
                        options.first.click()
                    except:
                        pass

                # Klikanie przycisku Dalej / Sprawdź
                try:
                    next_btn = page.locator("button:has-text('Dalej'), button:has-text('Sprawdź'), a:has-text('Dalej')")
                    if next_btn.count() > 0:
                        next_btn.first.click()
                except:
                    pass

                time.sleep(1.5)

            page.screenshot(path="final_success.png")
            print("=== ZAKOŃCZONO ===")

        except Exception as e:
            print(f"[X] Błąd: {e}")
            page.screenshot(path="error_final.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
