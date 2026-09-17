import os
import time
import random
from playwright.sync_api import sync_playwright

# Pobieranie danych z GitHub Secrets
USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

if not USERNAME or not PASSWORD:
    print("[X] BŁĄD: Brak danych logowania w GitHub Secrets! Upewnij się, że ustawiono LINGOS_USER i LINGOS_PASS.")
    exit(1)

def run():
    with sync_playwright() as p:
        # Uruchomienie przeglądarki Chromium w trybie headless
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Skrypt niszczący banery cookies i przeszkadzające nakładki na bieżąco
        page.add_init_script("""
            const removeCookies = () => {
                const selectors = [
                    '#CybotCookiebotDialog',
                    '#CybotCookiebotDialogBodyUnderlay',
                    '.cookie-banner',
                    '#cookie-notice',
                    'div[id*="cookie"]',
                    'div[class*="cookie"]',
                    '.modal-backdrop',
                    '.modal'
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
            };
            window.addEventListener('DOMContentLoaded', removeCookies);
            setInterval(removeCookies, 500);
        """)

        try:
            print("=== START BOT LINGOS ===")
            page.goto("https://lingos.pl/login", wait_until="networkidle")
            page.screenshot(path="01_login_page.png")

            # Próba fizycznego kliknięcia przycisku zgody (jeśli ukrył się w kodzie)
            try:
                cookie_btn = page.query_selector("button:has-text('Zaakceptuj'), button:has-text('Zgadzam się'), #CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                if cookie_btn and cookie_btn.is_visible():
                    cookie_btn.click(force=True)
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            print("Wprowadzanie danych logowania...")
            login_input = page.wait_for_selector("input[name='login'], input[name='email'], input[type='email']", timeout=10000)
            pass_input = page.wait_for_selector("input[name='password'], input[type='password']", timeout=10000)

            login_input.fill(USERNAME)
            pass_input.fill(PASSWORD)

            submit_btn = page.query_selector("button[type='submit'], input[type='submit']")
            if submit_btn:
                submit_btn.click()
            else:
                pass_input.press("Enter")

            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            page.screenshot(path="02_after_login.png")

            # Weryfikacja zalogowania
            content = page.content().lower()
            if "wyloguj" not in content and "moje grupy" not in content and "logout" not in content:
                print("[X] BŁĄD LOGOWANIA: Nie wykryto panelu użytkownika. Sprawdź poprawność loginu i hasła w Secrets!")
                page.screenshot(path="02_login_failed.png")
                exit(1)

            print("[OK] Zalogowano pomyślnie!")

            # Przejście do sekcji lekcji
            if "students/group" not in page.url:
                page.goto("https://lingos.pl/students/group", wait_until="networkidle")

            dictionary = {}
            solved_count = 0

            for step in range(80):
                page.wait_for_timeout(1000)
                page_content = page.content()

                # Warunek zakończenia lekcji
                if any(phrase in page_content for phrase in ["Koniec lekcji", "Brak słówek", "Gratulacje", "Lekcja ukończona"]):
                    print("[+] Lekcja została ukończona!")
                    page.screenshot(path="03_lesson_finished.png")
                    break

                # Szukanie pola do wpisywania odpowiedzi
                ans_input = page.query_selector("input[name='answer'], input[type='text']")
                if not ans_input:
                    # Próba kliknięcia przycisku startu lekcji, jeśli nie rozpoczęła się automatycznie
                    start_btn = page.query_selector("a:has-text('Rozpocznij'), a:has-text('Zacznij'), button:has-text('Dalej')")
                    if start_btn and start_btn.is_visible():
                        start_btn.click()
                        page.wait_for_load_state("networkidle")
                        continue
                    else:
                        print("[!] Brak aktywnych lekcji lub pola odpowiedzi.")
                        page.screenshot(path="03_no_input.png")
                        break

                # Odczyt słówka
                word_el = page.query_selector(".word-to-translate, h3, strong, .word-title")
                word_text = word_el.inner_text().strip() if word_el else "słówko"

                # Zapamiętywanie poprawnej odpowiedzi z podpowiedzi systemu
                correct_el = page.query_selector(".correct-answer, .alert-success, .translation")
                if correct_el:
                    dictionary[word_text] = correct_el.inner_text().strip()

                answer = dictionary.get(word_text, "")

                # Wpisanie odpowiedzi i losowa pauza (2-4s) chroniąca przed wykryciem bota
                ans_input.fill(answer)
                wait_time = random.randint(2, 4)
                print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Opóźnienie: {wait_time}s")
                time.sleep(wait_time)

                submit_btn = page.query_selector("button[type='submit'], input[type='submit']")
                if submit_btn:
                    submit_btn.click()
                else:
                    ans_input.press("Enter")

                page.wait_for_load_state("networkidle")
                solved_count += 1

            print(f"=== SUCCESS: Wykonano {solved_count} powtórek ===")
            page.screenshot(path="04_final.png")

        except Exception as e:
            print(f"[X] Wystąpił błąd podczas działania programu: {e}")
            page.screenshot(path="error.png")
            exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
