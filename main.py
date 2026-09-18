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

                # 1. SPRAWDZENIE CZY JESTEŚMY NA EKRANIE BŁĘDU (Przycisk Dalej / Enter)
                has_next = page.evaluate("""() => {
                    const elements = Array.from(document.querySelectorAll('button, a, div'));
                    return elements.some(el => el.innerText && el.innerText.includes('Dalej'));
                }""")

                if has_next:
                    # Wyciąganie słówka i poprawnej odpowiedzi z ekranu błędu
                    try:
                        parsed_data = page.evaluate("""() => {
                            const errDiv = document.querySelector('div.bg-red-100, div.border-red-500, div[class*="red"]');
                            if (!errDiv) return null;
                            const correctText = errDiv.innerText.replace('BŁĘDNA ODPOWIEDŹ', '').replace('volume_up', '').trim();
                            
                            let current = errDiv.previousElementSibling;
                            let promptText = '';
                            while (current) {
                                if (current.innerText && current.innerText.trim().length > 0 && !current.innerText.includes('Dalej')) {
                                    promptText = current.innerText.trim();
                                    break;
                                }
                                current = current.previousElementSibling;
                            }
                            return { prompt: promptText, answer: correctText.split('\\n').pop().trim() };
                        }""")

                        if parsed_data and parsed_data['prompt'] and parsed_data['answer']:
                            p_clean = parsed_data['prompt'].replace("PRZETŁUMACZ", "").strip()
                            dictionary[p_clean] = parsed_data['answer']
                            print(f"[ZAPAMIĘTANO] '{p_clean}' -> '{parsed_data['answer']}'")
                    except Exception as ex:
                        print(f"Błąd parsowania: {ex}")

                    # Wymuszenie kliknięcia + wysłanie klawisza Enter
                    page.evaluate("""() => {
                        const elements = Array.from(document.querySelectorAll('button, a, div'));
                        const btn = elements.find(el => el.innerText && el.innerText.includes('Dalej'));
                        if (btn) {
                            btn.click();
                            btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                        }
                    }""")
                    page.keyboard.press("Enter")
                    
                    print("Zatwierdzono błąd przez Enter/JS, czekam na nowe słówko...")
                    time.sleep(2.5)
                    continue

                # 2. OBSŁUGA POLA TEKSTOWEGO (Standardowe pytanie)
                text_input = page.locator("input[type='text']:not([readonly])").first
                if text_input.is_visible(timeout=1000):
                    current_word = page.evaluate("""() => {
                        const candidates = Array.from(document.querySelectorAll('h3, div.text-xl, div.text-2xl, div[class*="word"]'));
                        const valid = candidates.find(el => {
                            const t = el.innerText;
                            return t && !t.includes('Dalej') && !t.includes('PRZETŁUMACZ') && !t.includes('Odpowiedź') && t.length < 50;
                        });
                        return valid ? valid.innerText.replace('PRZETŁUMACZ', '').trim() : '';
                    }""")

                    answer_to_type = dictionary.get(current_word, "a")
                    print(f"[{i}] Pytanie: '{current_word}' -> Wpisuję: '{answer_to_type}'")
                    
                    text_input.fill(answer_to_type)
                    time.sleep(0.4)
                    text_input.press("Enter")
                    time.sleep(2.0)
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
