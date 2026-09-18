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

    dictionary = {}

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
                
                # Sprawdzenie czy to koniec lekcji
                if any(kw in content for kw in ["gratulacje", "podsumowanie", "ukończono", "lekcja wykonana", "dzisiaj powtórzone"]):
                    print("[+] Lekcja zrobiona w 100%!")
                    break

                # Pobranie aktualnego słówka do przetłumaczenia
                word_elem = page.locator("h3, .word-title, div:has-text('PRZETŁUMACZ') + div").first
                current_word = word_elem.inner_text().strip() if word_elem.is_visible() else ""

                # 1. SPRAWDZENIE CZY JESTEŚMY NA EKRANIE BŁĘDU (Przycisk Dalej)
                next_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej')").first
                if next_btn.is_visible(timeout=1000):
                    # Wyciąganie poprawnej odpowiedzi z czerwonej ramki
                    try:
                        red_box = page.locator("div.bg-red-100, div.border-red-500").first
                        if red_box.is_visible(timeout=300):
                            box_text = red_box.inner_text().replace("BŁĘDNA ODPOWIEDŹ", "").strip()
                            lines = [l.strip() for l in box_text.split('\n') if l.strip()]
                            correct_text = lines[-1] if lines else box_text
                            if current_word and correct_text:
                                dictionary[current_word] = correct_text
                                print(f"Zapamiętano do słownika: '{current_word}' -> '{correct_text}'")
                    except:
                        pass
                    
                    # Kliknięcie przycisku "Dalej"
                    try:
                        next_btn.click()
                    except:
                        page.evaluate("document.querySelector('button.btn-success, button:not([disabled])').click();")
                    
                    # KLUCZOWE: Czekamy aż ekran błędu zniknie i pojawi się pole tekstowe nowgo słówka
                    time.sleep(2.0)
                    continue

                # 2. OBSŁUGA POLA TEKSTOWEGO (Wpisywanie odpowiedzi)
                text_input = page.locator("input[type='text']:not([readonly])").first
                if text_input.is_visible(timeout=1500):
                    answer_to_type = dictionary.get(current_word, "a")
                    print(f"Wpisuję słówko '{current_word}' -> '{answer_to_type}'")
                    text_input.fill(answer_to_type)
                    time.sleep(0.5)
                    text_input.press("Enter")
                    time.sleep(2.0) # Czekamy na odpowiedź serwera Lingos
                    continue

                # 3. OBSŁUGA KAFELKÓW (Wielokrotny wybór)
                options = page.locator(".answer-tile, .word-tile, div.option, button.answer-btn")
                if options.count() > 0:
                    try:
                        options.first.click()
                        time.sleep(1.5)
                    except:
                        pass

                time.sleep(0.5)

            page.screenshot(path="final_success.png")
            print("=== ZAKOŃCZONO SESJĘ ===")

        except Exception as e:
            print(f"[X] Błąd: {e}")
            page.screenshot(path="error_final.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
