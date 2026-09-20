import os
import sys
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

MAX_ROUNDS = 300


def visible(locator):
    try:
        return locator.count() > 0 and locator.first.is_visible()
    except Exception:
        return False


def body_text(page):
    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def screenshot(page, name):
    try:
        page.screenshot(path=name, full_page=True)
        print(f"[SCREENSHOT] {name}")
    except Exception as e:
        print(f"[!] Nie udało się zrobić screenshotu: {e}")


def get_buttons(page):
    result = []

    try:
        buttons = page.locator("button").all()

        for i, button in enumerate(buttons):
            try:
                if button.is_visible():
                    text = button.inner_text().strip().replace("\n", " ")

                    if text:
                        result.append((i, text))
            except Exception:
                pass

    except Exception:
        pass

    return result


def print_page_state(page, prefix=""):
    print()
    print(f"========== {prefix} ==========")
    print("URL:", page.url)

    try:
        print("TITLE:", page.title())
    except Exception:
        pass

    print("PRZYCISKI:")

    for number, text in get_buttons(page):
        print(f"  [{number}] {text}")

    try:
        inputs = page.locator("input").all()

        print("INPUTY:")

        for i, inp in enumerate(inputs):
            try:
                if inp.is_visible():
                    print(
                        f"  [{i}] "
                        f"type={inp.get_attribute('type')} "
                        f"placeholder={inp.get_attribute('placeholder')}"
                    )
            except Exception:
                pass

    except Exception:
        pass

    print("================================")
    print()


def find_text_input(page):
    """
    Najważniejsze:
    Szukamy pola odpowiedzi PRZED przyciskiem "Dalej".
    """

    selectors = [
        "input[placeholder='Twoja odpowiedź']:not([readonly]):not([disabled])",
        "input[placeholder*='Twoja odpowiedź']:not([readonly]):not([disabled])",
        "input[type='text']:not([readonly]):not([disabled])",
        "input:not([type]):not([readonly]):not([disabled])",
        "textarea:not([readonly]):not([disabled])",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector)

            for i in range(locator.count()):
                element = locator.nth(i)

                if element.is_visible():
                    return element

        except Exception:
            pass

    return None


def find_next_button(page):
    selectors = [
        "button:has-text('Dalej')",
        "a:has-text('Dalej')",
        "button:has-text('Kontynuuj')",
        "button:has-text('Następne')",
        "button:has-text('Następny')",
        "button:has-text('Next')",
        "button:has-text('Continue')",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector)

            for i in range(locator.count()):
                element = locator.nth(i)

                if element.is_visible():
                    return element

        except Exception:
            pass

    return None


def get_current_prompt(page):
    """
    Próbuje znaleźć aktualne polskie słowo/zwrot.
    """

    selectors = [
        "[class*='word']",
        "[class*='question']",
        "h1",
        "h2",
        "h3",
        "[class*='text-3xl']",
        "[class*='text-2xl']",
        "[class*='text-xl']",
    ]

    ignored = {
        "przetłumacz",
        "tłumaczenie",
        "dalej",
        "sprawdź",
        "kontynuuj",
        "next",
        "continue",
        "twoja odpowiedź",
    }

    for selector in selectors:

        try:
            locator = page.locator(selector)

            count = min(locator.count(), 20)

            for i in range(count):

                element = locator.nth(i)

                if not element.is_visible():
                    continue

                text = element.inner_text().strip()
                text = " ".join(text.split())

                if not text:
                    continue

                if text.lower() in ignored:
                    continue

                if len(text) > 150:
                    continue

                return text

        except Exception:
            pass

    return ""


def extract_correct_answer(page):
    """
    Próbuje znaleźć poprawną odpowiedź po błędnym tłumaczeniu.
    """

    selectors = [
        "div.bg-red-100",
        "div.border-red-500",
        "[class*='red-100']",
        "[class*='border-red']",
        "[class*='incorrect']",
        "[class*='error']",
    ]

    for selector in selectors:

        try:
            locator = page.locator(selector)

            for i in range(locator.count()):

                element = locator.nth(i)

                if not element.is_visible():
                    continue

                text = element.inner_text().strip()

                if not text:
                    continue

                lines = [
                    " ".join(line.split())
                    for line in text.splitlines()
                    if line.strip()
                ]

                cleaned = []

                for line in lines:

                    low = line.lower()

                    if "błędna odpowiedź" in low:
                        continue

                    if "poprawna odpowiedź" in low:
                        continue

                    if "incorrect" in low:
                        continue

                    if "correct answer" in low:
                        continue

                    if "volume_up" in low:
                        continue

                    if low == "dalej":
                        continue

                    cleaned.append(line)

                if cleaned:
                    return cleaned[-1]

        except Exception:
            pass

    return ""


def is_completion_screen(page):
    text = body_text(page).lower()

    completion_words = [
        "gratulacje",
        "podsumowanie",
        "ukończono",
        "lekcja wykonana",
        "dzisiaj powtórzone",
        "zakończono",
        "lekcja ukończona",
        "wynik końcowy",
        "sesja zakończona",
    ]

    return any(word in text for word in completion_words)


def click_next_and_wait(page):
    """
    Klikamy "Dalej" tylko wtedy, gdy nie ma już pola odpowiedzi.
    """

    button = find_next_button(page)

    if button is None:
        return False

    try:

        before_url = page.url
        before_body = body_text(page)

        print("[INFO] Klikam 'Dalej'...")

        button.scroll_into_view_if_needed()
        button.click(timeout=3000)

        deadline = time.time() + 5

        while time.time() < deadline:

            time.sleep(0.25)

            if is_completion_screen(page):
                print("[OK] Wykryto ekran zakończenia.")
                return True

            if page.url != before_url:
                print("[OK] URL zmienił się.")
                return True

            if body_text(page) != before_body:
                print("[OK] Zawartość strony zmieniła się.")
                return True

            if find_text_input(page) is not None:
                print("[OK] Pojawiło się pole odpowiedzi.")
                return True

        print("[!] Po kliknięciu 'Dalej' ekran się nie zmienił.")

        return False

    except Exception as e:

        print(f"[!] Błąd kliknięcia 'Dalej': {e}")

        return False


def submit_answer(page, text_input, answer):
    """
    Wpisuje odpowiedź i zatwierdza ją.
    """

    try:

        text_input.fill(answer)

        print(f"[INFO] Wpisuję odpowiedź: '{answer}'")

        try:
            text_input.press("Enter")
        except Exception:
            page.keyboard.press("Enter")

        time.sleep(1.5)

        return True

    except Exception as e:

        print(f"[!] Nie udało się wysłać odpowiedzi: {e}")

        return False


def run():

    if not USERNAME or not PASSWORD:

        print(
            "[X] BŁĄD: Brak LINGOS_USER lub LINGOS_PASS "
            "w GitHub Secrets!"
        )

        sys.exit(1)

    dictionary = {}

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            viewport={
                "width": 1280,
                "height": 720
            },
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="pl-PL"
        )

        page = context.new_page()

        try:

            print("======================================")
            print("       START SESJI LINGOS")
            print("======================================")

            # ==================================================
            # LOGOWANIE
            # ==================================================

            print("[1] Otwieram stronę logowania...")

            page.goto(
                "https://lingos.pl/h/login",
                wait_until="domcontentloaded",
                timeout=30000
            )

            time.sleep(2)

            try:

                page.evaluate(
                    """
                    document.getElementById(
                        'CybotCookiebotDialog'
                    )?.remove();
                    """
                )

            except Exception:
                pass

            print("[2] Wpisuję dane logowania...")

            email_input = page.locator(
                "input[type='email'], "
                "input[placeholder*='Email'], "
                "input[placeholder*='email'], "
                "input[type='text']"
            ).first

            password_input = page.locator(
                "input[type='password']"
            ).first

            email_input.wait_for(
                state="visible",
                timeout=10000
            )

            password_input.wait_for(
                state="visible",
                timeout=10000
            )

            email_input.fill(USERNAME)
            password_input.fill(PASSWORD)

            login_button = page.locator(
                "button:has-text('Zaloguj się'), "
                "button:has-text('Zaloguj'), "
                "button[type='submit']"
            ).first

            login_button.click()

            print("[3] Czekam na zalogowanie...")

            try:

                page.wait_for_load_state(
                    "networkidle",
                    timeout=15000
                )

            except PlaywrightTimeoutError:

                print(
                    "[!] networkidle timeout — kontynuuję."
                )

            time.sleep(3)

            print_page_state(
                page,
                "PO LOGOWANIU"
            )

            # ==================================================
            # PRZEJŚCIE DO NAUKI
            # ==================================================

            print("[4] Szukam 'Ucz się'...")

            learn_button = page.locator(
                "button:has-text('Ucz się'), "
                "a:has-text('Ucz się')"
            ).first

            if visible(learn_button):

                print("[OK] Znaleziono 'Ucz się'.")

                learn_button.click()

                try:

                    page.wait_for_load_state(
                        "networkidle",
                        timeout=10000
                    )

                except PlaywrightTimeoutError:
                    pass

                time.sleep(3)

            else:

                print(
                    "[INFO] Nie znaleziono przycisku "
                    "'Ucz się'. Otwieram /learning..."
                )

                page.goto(
                    "https://lingos.pl/learning",
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                time.sleep(4)

            print_page_state(
                page,
                "EKRAN NAUKI"
            )

            screenshot(
                page,
                "start_learning.png"
            )

            # ==================================================
            # PĘTLA NAUKI
            # ==================================================

            print("======================================")
            print("      ROZPOCZYNAM NAUKĘ")
            print("======================================")

            stuck_counter = 0
            completed = False

            for i in range(1, MAX_ROUNDS + 1):

                # --------------------------------------------------
                # 1. NAJPIERW SPRAWDZAMY ZAKOŃCZENIE
                # --------------------------------------------------

                if is_completion_screen(page):

                    print()
                    print("======================================")
                    print("[+] WYKRYTO ZAKOŃCZENIE LEKCJI!")
                    print("======================================")

                    completed = True
                    break

                # --------------------------------------------------
                # 2. NAJWAŻNIEJSZE:
                #    JEŻELI JEST POLE "TWOJA ODPOWIEDŹ",
                #    TO OBSŁUGUJEMY JE PIERWSZE.
                #
                #    NIE WOLNO WTEDY KLIKAĆ "DALEJ".
                # --------------------------------------------------

                text_input = find_text_input(page)

                if text_input is not None:

                    current_word = get_current_prompt(page)

                    print()
                    print(
                        f"[{i}] EKRAN ODPOWIEDZI"
                    )

                    print(
                        f"[{i}] Aktualne słowo: "
                        f"'{current_word}'"
                    )

                    # --------------------------------------------------
                    # ZNANA ODPOWIEDŹ
                    # --------------------------------------------------

                    if current_word and current_word in dictionary:

                        answer = dictionary[current_word]

                        print(
                            f"[{i}] Znalazłem zapamiętaną "
                            f"odpowiedź: '{answer}'"
                        )

                    else:

                        # Pierwszy kontakt z nowym słowem.
                        # Pusta odpowiedź powoduje pokazanie poprawnej
                        # odpowiedzi przez Lingos.
                        answer = ""

                        print(
                            f"[{i}] Nie znam jeszcze odpowiedzi."
                        )

                    success = submit_answer(
                        page,
                        text_input,
                        answer
                    )

                    if not success:

                        stuck_counter += 1

                    else:

                        stuck_counter = 0

                    time.sleep(0.5)

                    continue

                # --------------------------------------------------
                # 3. DOPIERO TERAZ SPRAWDZAMY "DALEJ"
                # --------------------------------------------------

                next_button = find_next_button(page)

                if next_button is not None:

                    print()
                    print(
                        f"[{i}] EKRAN Z PRZYCISKIEM 'DALEJ'."
                    )

                    prompt = get_current_prompt(page)
                    correct = extract_correct_answer(page)

                    # --------------------------------------------------
                    # ZAPAMIĘTANIE POPRAWNEJ ODPOWIEDZI
                    # --------------------------------------------------

                    if prompt and correct:

                        dictionary[prompt] = correct

                        print(
                            f"[ZAPAMIĘTANO] "
                            f"'{prompt}' -> '{correct}'"
                        )

                    elif correct:

                        print(
                            f"[INFO] Poprawna odpowiedź: "
                            f"{correct}"
                        )

                    else:

                        print(
                            "[INFO] Nie udało się odczytać "
                            "poprawnej odpowiedzi."
                        )

                    # --------------------------------------------------
                    # KLIKNIĘCIE DALEJ
                    # --------------------------------------------------

                    success = click_next_and_wait(page)

                    if not success:

                        stuck_counter += 1

                        print(
                            f"[!] Brak przejścia "
                            f"({stuck_counter}/3)."
                        )

                        if stuck_counter >= 3:

                            screenshot(
                                page,
                                f"stuck_{i}.png"
                            )

                            print_page_state(
                                page,
                                f"ZAWIESZENIE {i}"
                            )

                            raise RuntimeError(
                                "Lingos nie przechodzi "
                                "z ekranu 'Dalej'."
                            )

                    else:

                        stuck_counter = 0

                    time.sleep(0.7)

                    continue

                # --------------------------------------------------
                # 4. NIEZNANY EKRAN
                # --------------------------------------------------

                print()
                print(
                    f"[{i}] Nie rozpoznano aktualnego ekranu."
                )

                stuck_counter += 1

                if stuck_counter >= 5:

                    print(
                        "[X] Strona nie zmienia się "
                        "i nie rozpoznaję elementów."
                    )

                    screenshot(
                        page,
                        "unknown_screen.png"
                    )

                    print_page_state(
                        page,
                        "NIEZNANY EKRAN"
                    )

                    raise RuntimeError(
                        "Nie udało się rozpoznać "
                        "ekranu Lingosa."
                    )

                time.sleep(1)

            # ==================================================
            # KONIEC
            # ==================================================

            screenshot(
                page,
                "final_success.png"
            )

            print()
            print("======================================")

            if completed:

                print("       SESJA ZAKOŃCZONA")

            else:

                print(
                    "       Osiągnięto limit "
                    f"{MAX_ROUNDS} rund"
                )

            print("======================================")

            print()
            print("Zapamiętane słowa:")

            if dictionary:

                for word, answer in dictionary.items():

                    print(
                        f"  {word} -> {answer}"
                    )

            else:

                print("  Brak.")

            if not completed:

                sys.exit(1)

        except Exception as e:

            print()
            print("======================================")
            print("[X] BŁĄD")
            print("======================================")

            print(e)

            screenshot(
                page,
                "error_final.png"
            )

            print_page_state(
                page,
                "STAN PO BŁĘDZIE"
            )

            sys.exit(1)

        finally:

            browser.close()


if __name__ == "__main__":
    run()