import os
import time
import random
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

if not USERNAME or not PASSWORD:
    print("[X] BŁĄD: Brak danych w GitHub Secrets (LINGOS_USER, LINGOS_PASS)!")
    exit(1)

with sync_playwright() as p:
    print("1. Uruchamianie wirtualnej przeglądarki Chrome...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()

    print("2. Otwieranie strony logowania Lingos.pl...")
    page.goto("https://lingos.pl/login", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Usuwanie okna zgody na cookies (Cookiebot)
    page.evaluate("""() => {
        const dialog = document.getElementById('CybotCookiebotDialog');
        if (dialog) dialog.remove();
        const overlay = document.getElementById('CybotCookiebotDialogBodyUnderlay');
        if (overlay) overlay.remove();
    }""")

    # Szukanie pola logowania
    try:
        page.wait_for_selector("input[name='login'], input[name='email'], input[type='text']:not([type='hidden'])", state="visible", timeout=10000)
    except Exception:
        print("[!] Próba przejścia na alternatywny adres /h/login...")
        page.goto("https://lingos.pl/h/login", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

    print("3. Wpisywanie danych logowania...")
    login_input = page.query_selector("input[name='login'], input[name='email'], input[type='text']:not([type='hidden'])")
    pass_input = page.query_selector("input[type='password']")

    if not login_input or not pass_input:
        print("[X] BŁĄD: Nie odnaleziono formularza logowania!")
        page.screenshot(path="01_login_error.png")
        browser.close()
        exit(1)

    login_input.fill(USERNAME)
    pass_input.fill(PASSWORD)
    
    submit_btn = page.query_selector("button[type='submit'], input[type='submit']")
    if submit_btn:
        submit_btn.click(force=True)
    else:
        pass_input.press("Enter")

    page.wait_for_timeout(4000)
    page.screenshot(path="02_after_login.png")

    print(f"--> Adres URL po logowaniu: {page.url}")

    # Sprawdzenie czy zalogowano
    if "login" in page.url.lower() and "student" not in page.url.lower():
        print("[X] BŁĄD LOGOWANIA: Odrzucono login lub hasło!")
        browser.close()
        exit(1)

    print("[OK] Zalogowano! Przeszukiwanie pulpitu w poszukiwaniu lekcji...")

    # Szukanie linku do lekcji na pulpicie
    links = page.query_selector_all("a")
    found_lesson_url = None

    print(f"--> Odnaleziono {len(links)} linków na stronie głównej.")
    for link in links:
        href = link.get_attribute("href") or ""
        text = link.inner_text().strip().lower()
        if any(keyword in href for keyword in ["learning", "lesson", "start", "group", "lekcja"]) or any(keyword in text for keyword in ["rozpocznij", "zacznij", "wykonaj", "lekcja", "start"]):
            if "login" not in href and "logout" not in href:
                print(f"    [+] Znaleziono link: '{link.inner_text().strip()}' -> {href}")
                found_lesson_url = href
                break

    if found_lesson_url:
        target_url = "https://lingos.pl" + found_lesson_url if found_lesson_url.startswith("/") else found_lesson_url
        print(f"--> Wchodzenie w lekcję: {target_url}")
        page.goto(target_url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
    else:
        print("[!] Brak bezpośredniego linku. Próba przejścia na /students...")
        page.goto("https://lingos.pl/students", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

    page.screenshot(path="03_lesson_page.png")

    # 4. Rozwiązywanie słówek
    dictionary = {}
    solved_count = 0

    print("5. Rozpoczynanie pętli ze słówkami...")
    for step in range(50):
        page.evaluate("""() => {
            const dialog = document.getElementById('CybotCookiebotDialog');
            if (dialog) dialog.remove();
        }""")

        content = page.content().lower()
        if any(term in content for term in ["koniec lekcji", "gratulacje", "podsumowanie lekcji", "brak słówek", "ukończono"]):
            print("[+] SUKCES! Lekcja została w pełni ukończona.")
            break

        ans_input = page.query_selector("input[type='text']:not([readonly]):not([type='hidden'])")

        if not ans_input:
            next_btn = page.query_selector("button:has-text('Dalej'), a:has-text('Dalej'), input[value='Dalej'], button:has-text('Następne')")
            if next_btn:
                print("    [->] Klikanie 'Dalej'...")
                next_btn.click(force=True)
                page.wait_for_timeout(2000)
                continue
            else:
                print("[!] Brak pola odpowiedzi. Koniec pętli.")
                break

        word_el = page.query_selector(".word-to-translate, h3, strong, .word, .question")
        word_text = word_el.inner_text().strip() if word_el else f"Słówko #{step+1}"

        answer = dictionary.get(word_text, "")

        ans_input.fill(answer)
        wait = random.randint(2, 4)
        print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Czekam {wait}s...")
        time.sleep(wait)

        submit_btn = page.query_selector("button[type='submit'], input[type='submit']")
        if submit_btn:
            submit_btn.click(force=True)
        else:
            ans_input.press("Enter")

        page.wait_for_timeout(2500)

        correct_el = page.query_selector(".correct-answer, .alert-success, .translation-correct, .badge-success")
        if correct_el:
            correct_text = correct_el.inner_text().strip()
            dictionary[word_text] = correct_text
            print(f"    --> Zapamiętano poprawną odpowiedź: '{correct_text}'")

        solved_count += 1

    page.screenshot(path="04_final_state.png")

    # Jeśli zrobiono 0 słówek -> WYMUSZANIE BŁĘDU (Żeby GitHub nie pokazywał zielonego ptaszka)
    if solved_count == 0:
        print("[X] BŁĄD: Zrobiono 0 słówek! Pobierz pliki .png z sekcji Artifacts na GitHubie, aby zobaczyć zrzut ekranu.")
        browser.close()
        exit(1)

    print(f"=== SUKCES: Wykonano kroków/słówek: {solved_count} ===")
    browser.close()
