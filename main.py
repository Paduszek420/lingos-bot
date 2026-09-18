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

            try:
                page.evaluate("document.getElementById('CybotCookiebotDialog')?.remove();")
            except:
                pass

            print("Wpisuję dane logowania...")
            page.locator("input[type='email'], input[type='text'], input[placeholder*='Email']").first.fill(USERNAME)
            page.locator("input[type='password']").first.fill(PASSWORD)
            page.locator("button:has-text('Zaloguj się'), button[type='submit']").first.click()
            
            print("Czekam na zalogowanie...")
            page.wait_for_load_state("networkidle")
            time.sleep(4)

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

            print("Rozpoczynam rozwiązywanie słówek...")
            for i in range(1, 150):
                content = page.inner_text("body").lower()
                
                if any(kw in content for kw in ["gratulacje", "podsumowanie", "ukończono", "lekcja wykonana", "dzisiaj powtórzone"]):
                    print("[+] Lekcja zrobiona w 100%!")
                    break

                # 1. SPRAWDZENIE CZY JESTEŚMY NA EKRANIE BŁĘDU (Przycisk Dalej)
                dalej_btn = page.locator("button:has-text('Dalej'), a:has-text('Dalej')").first
                
                if dalej_btn.is_visible(timeout=800):
                    # Próba zapamiętania słówka i poprawnej odpowiedzi z ekranu błędu
                    try:
                        red_box = page.locator("div.bg-red-100, div.border-red-500, div[class*='red']").first
                        if red_box.is_visible(timeout=300):
                            box_text = red_box.inner_text().replace("BŁĘDNA ODPOWIEDŹ", "").replace("volume_up", "").strip()
                            lines = [l.strip() for l in box_text.split('\n') if l.strip()]
                            correct_text = lines[-1] if lines else box_text
                            
                            prompt_elem = red_box.locator("xpath=preceding-sibling::*[not(contains(text(), 'Dalej'))][1]").first
                            prompt_text = prompt_elem.inner_text().replace("PRZETŁUMACZ", "").strip() if prompt_elem.is_visible() else ""
                            
                            if prompt_text and correct_text:
                                dictionary[prompt_text] = correct_text
                                print(f"[ZAPAMIĘTANO] '{prompt_text}' -> '{correct_text}'")
                    except:
                        pass

                    print(f"[{i}] Zatwierdzam ekran błędu przez Enter...")
                    # Agresywne uderzenie w klawisz Enter, który wymusza przejście na Lingosie
                    page.keyboard.press("Enter")
                    time.sleep(0.5)
                    try:
                        dalej_btn.click(force=True)
                    except:
                        pass
                    
                    time.sleep(1.5)
                    continue

                # 2. STANDARDOWE POLE TEKSTOWE
                text_input = page.locator("input[type='text']:not([readonly])").first
                if text_input.is_visible(timeout=800):
                    current_word = ""
                    try:
                        word_elem = page.locator("h3, div.text-xl, div.text-2xl, div[class*='word']").first
                        if word_elem.is_visible():
                            current_word = word_elem.inner_text().replace("PRZETŁUMACZ", "").strip()
                    except:
                        pass

                    answer_to_type = dictionary.get(current_word, "a")
                    print(f"[{i}] Słowo: '{current_word}' -> Wpisuję: '{answer_to_type}'")
                    
                    text_input.fill(answer_to_type)
                    time.sleep(0.3)
                    text_input.press("Enter")
                    time.sleep(1.5)
                    continue

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
