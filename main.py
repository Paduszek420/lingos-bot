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
                    '.modal',
                    '#gdpr-banner'
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
            print("Otwieranie strony głównej https://lingos.pl/ ...")
            page.goto("https://lingos.pl/", wait_until="networkidle")
            page.wait_for_timeout(2000)
            page.screenshot(path="01_login_page.png")

            # Próba otwarcia formularza logowania, jeśli przycisk 'Zaloguj' jest osobno
            try:
                login_btn = page.query_selector("a:has-text('Zaloguj'), button:has-text('Zaloguj')")
                if login_btn and login_btn.is_visible():
                    login_btn.click()
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            # Próba fizycznego kliknięcia przycisku zgody cookies (jeśli został)
            try:
                cookie_btn = page.query_selector("button:has-text('Zaakceptuj'), button:has-text('Zgadzam się'), #CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                if cookie_btn and cookie_btn.is_visible():
                    cookie_btn.click(force=True)
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            print("Wprowadzanie danych logowania...")
            login_input = page.wait_for_selector(
                "input[name*='login'], input[name*='email'], input[name*='username'], input[type='email'], input[type='text']", 
                timeout=10000
            )
            pass_input = page.wait_for_selector(
                "input[name*='pass'], input[type='password']", 
                timeout=10000
            )

            login_input.fill(USERNAME)
            pass_input.fill(PASSWORD)

            submit_btn = page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Zaloguj')")
            if submit_btn and submit_btn.is_visible():
                submit_btn.click()
            else:
                pass_input.press("Enter")

            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            page.screenshot(path="02_after_login.png")

            # Weryfikacja zalogowania
            content = page.content().lower()
            if "wyloguj" not in content and "moje grupy" not in content and "logout" not in content and "lekcj" not in content and "słówk" not in content:
                print("[X] BŁĄD LOGOWANIA: Nie wykryto panelu użytkownika. Sprawdź poprawność loginu i hasła w Secrets!")
                page.screenshot(path="02_login_failed.png")
                exit(1)

            print("[OK] Zalogowano pomyślnie!")

            # Szukanie przycisku/linku do lekcji lub grupy
            lesson_link = page.query_selector("a:has-text('Rozpocznij'), a:has-text('Zacznij'), a:has-text('Ucz się'), a:has-text('Powtórka'), a:has-text('Lekcja'), a[href*='lesson'], a[href*='group']")
            if lesson_link and lesson_link.is_visible():
                print("Przechodzenie do lekcji/grupy...")
                lesson_link.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1000)

            dictionary = {}
            solved_count = 0

            for step in range(80):
                page.wait_for_timeout(1000)
                page_content = page.content()

                # Warunek zakończenia lekcji
                if any(phrase in page_content.lower() for phrase in ["koniec lekcji", "brak słówek", "gratulacje", "lekcja ukończona", "brawo"]):
                    print("[+] Lekcja została ukończona!")
                    page.screenshot(path="03_lesson_finished.png")
                    break

                # Szukanie pola do wpisywania odpowiedzi
                ans_input = page.query_selector("input[name*='answer'], input[name*='odpowiedz'], input[type='text']")
                if not ans_input or not ans_input.is_visible():
                    # Próba kliknięcia przycisku startu/kontynuacji
                    start_btn = page.query_selector("a:has-text('Rozpocznij'), a:has-text('Zacznij'), button:has-text('Dalej'), button:has-text('Start'), a:has-text('Dalej')")
                    if start_btn and start_btn.is_visible():
                        start_btn.click()
                        page.wait_for_load_state("networkidle")
                        continue
                    else:
                        print("[!] Brak aktywnego pola odpowiedzi. Podsumowanie kroku.")
                        page.screenshot(path="03_no_input.png")
                        break

                # Odczyt słówka do przetłumaczenia
                word_el = page.query_selector(".word-to-translate, .word, h3, h2, strong, .word-title, .sentence")
                word_text = word_el.inner_text().strip() if word_el else "słówko"

                # Zapamiętywanie poprawnej odpowiedzi, jeśli strona pokazała ją po błędzie
                correct_el = page.query_selector(".correct-answer, .alert-success, .translation, .badge-success")
                if correct_el and correct_el.is_visible():
                    dictionary[word_text] = correct_el.inner_text().strip()

                answer = dictionary.get(word_text, "")

                # Wpisanie odpowiedzi i losowa pauza (2-4s) chroniąca przed wykryciem bota
                ans_input.fill(answer)
                wait_time = random.randint(2, 4)
                print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Opóźnienie: {wait_time}s")
                time.sleep(wait_time)

                submit_btn = page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Sprawdź'), button:has-text('Dalej')")
                if submit_btn and submit_btn.is_visible():
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
