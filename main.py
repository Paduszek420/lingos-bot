import os
import sys
import time
import re

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
        return page.locator("body").inner_text(timeout=3000).strip()
    except Exception:
        return ""


def screenshot(page, name):
    try:
        page.screenshot(path=f"{name}.png", full_page=True)
    except Exception:
        pass


def get_buttons(page):
    result = []

    try:
        buttons = page.locator("button")
        for i in range(buttons.count()):
            b = buttons.nth(i)

            if not b.is_visible():
                continue

            try:
                txt = b.inner_text().strip()
            except Exception:
                txt = ""

            if txt:
                result.append(txt)

    except Exception:
        pass

    return result


def print_page_state(page, prefix=""):
    try:
        print(f"{prefix}URL: {page.url}")
        print(f"{prefix}PRZYCISKI: {get_buttons(page)}")

        inputs = page.locator("input")
        input_info = []

        for i in range(inputs.count()):
            el = inputs.nth(i)

            try:
                if not el.is_visible():
                    continue

                input_info.append(
                    f"type={el.get_attribute('type')} "
                    f"placeholder={el.get_attribute('placeholder')}"
                )
            except Exception:
                pass

        print(f"{prefix}INPUTY: {input_info}")

    except Exception as e:
        print(f"[WARN] Nie można odczytać stanu strony: {e}")


def find_text_input(page):
    """
    NAJWAŻNIEJSZE:
    Jeśli istnieje input 'Twoja odpowiedź', zawsze traktujemy ekran
    jako ekran wpisywania odpowiedzi.
    """

    selectors = [
        "input[placeholder='Twoja odpowiedź']",
        "textarea[placeholder='Twoja odpowiedź']",
        "input[placeholder*='Twoja odpowiedź']",
        "textarea[placeholder*='Twoja odpowiedź']",
        "input[type='text']",
        "textarea",
    ]

    for selector in selectors:
        try:
            loc = page.locator(selector)

            for i in range(loc.count()):
                el = loc.nth(i)

                if el.is_visible():
                    return el

        except Exception:
            pass

    return None


def find_next_button(page):
    selectors = [
        "button:has-text('Dalej')",
        "button:has-text('dalej')",
        "text=Dalej",
    ]

    for selector in selectors:
        try:
            loc = page.locator(selector)

            for i in range(loc.count()):
                el = loc.nth(i)

                if el.is_visible():
                    return el

        except Exception:
            pass

    return None


def normalize_text(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_prompt(page):
    """
    Wyciąga TYLKO słowo/zwrot po 'PRZETŁUMACZ'.

    Przykład:
        0/20 PRZETŁUMACZ wpaść do kogoś Dalej [Enter]

    wynik:
        wpaść do kogoś
    """

    text = normalize_text(body_text(page))

    if not text:
        return ""

    patterns = [
        r"PRZETŁUMACZ\s+(.+?)\s+Dalej(?:\s+\[Enter\])?",
        r"PRZETŁUMACZ\s+(.+?)\s+Dalej",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            result = normalize_text(match.group(1))

            # Usuwamy ewentualne elementy licznika.
            result = re.sub(r"^\d+\s*/\s*\d+\s*", "", result)

            return result.strip()

    # Awaryjnie próbujemy znaleźć element zawierający "PRZETŁUMACZ".
    try:
        elements = page.locator("text=PRZETŁUMACZ")

        for i in range(elements.count()):
            el = elements.nth(i)

            if not el.is_visible():
                continue

            try:
                parent = el.locator("..")
                parent_text = normalize_text(parent.inner_text())

                match = re.search(
                    r"PRZETŁUMACZ\s+(.+?)(?:\s+Dalej|\s+\[Enter\]|$)",
                    parent_text,
                    re.IGNORECASE,
                )

                if match:
                    return normalize_text(match.group(1))

            except Exception:
                pass

    except Exception:
        pass

    return ""


def extract_result_answer(page):
    """
    Wyciąga odpowiedź z ekranu po błędnej odpowiedzi.

    Przykład:
        0/20 BŁĘDNA ODPOWIEDŹ wpaść do kogoś come over Dalej [Enter]

    wynik:
        ('wpaść do kogoś', 'come over')
    """

    text = normalize_text(body_text(page))

    if not text:
        return "", ""

    # Najpierw próbujemy znaleźć cały fragment.
    patterns = [
        r"BŁĘDNA ODPOWIEDŹ\s+(.+?)\s+([^\s].*?)\s+Dalej(?:\s+\[Enter\])?",
        r"POPRAWNA ODPOWIEDŹ\s+(.+?)\s+([^\s].*?)\s+Dalej(?:\s+\[Enter\])?",
        r"DOBRA ODPOWIEDŹ\s+(.+?)\s+([^\s].*?)\s+Dalej(?:\s+\[Enter\])?",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            prompt = normalize_text(match.group(1))
            answer = normalize_text(match.group(2))

            prompt = re.sub(r"^\d+\s*/\s*\d+\s*", "", prompt)

            return prompt, answer

    # Jeśli parser wyniku nie zadziała, wykorzystujemy aktualny prompt
    # oraz próbujemy znaleźć tekst przed "Dalej".
    prompt = extract_prompt(page)

    if prompt:
        try:
            # Szukamy fragmentu:
            # prompt + odpowiedź + Dalej
            escaped_prompt = re.escape(prompt)

            match = re.search(
                escaped_prompt + r"\s+(.+?)\s+Dalej",
                text,
                re.IGNORECASE,
            )

            if match:
                answer = normalize_text(match.group(1))

                if answer and answer.lower() != prompt.lower():
                    return prompt, answer

        except Exception:
            pass

    return "", ""


def is_result_screen(page):
    text = normalize_text(body_text(page)).lower()

    result_markers = [
        "błędna odpowiedź",
        "poprawna odpowiedź",
        "dobra odpowiedź",
    ]

    return any(marker in text for marker in result_markers)


def is_completion_screen(page):
    text = normalize_text(body_text(page)).lower()

    markers = [
        "ukończono",
        "gratulacje",
        "koniec",
        "zakończono",
        "lekcja zakończona",
    ]

    return any(marker in text for marker in markers)


def click_next_and_wait(page):
    button = find_next_button(page)

    if not button:
        print("[WARN] Nie znaleziono przycisku 'Dalej'.")
        return False

    try:
        print("[INFO] Klikam 'Dalej'...")

        old_text = normalize_text(body_text(page))

        button.click()

        # Dajemy Lingosowi czas na zmianę ekranu.
        for _ in range(30):
            time.sleep(0.2)

            new_text = normalize_text(body_text(page))

            if new_text != old_text:
                print("[OK] Zawartość strony zmieniła się.")
                return True

        print("[WARN] Strona nie zgłosiła wyraźnej zmiany.")

        return True

    except Exception as e:
        print(f"[ERROR] Kliknięcie 'Dalej' nie powiodło się: {e}")
        return False


def submit_answer(page, text_input, answer):
    try:
        print(f"[INFO] Wpisuję odpowiedź: '{answer}'")

        text_input.click()
        text_input.fill(answer)

        # Enter powinien zatwierdzić odpowiedź.
        text_input.press("Enter")

        time.sleep(1)

        return True

    except Exception as e:
        print(f"[ERROR] Nie udało się wpisać odpowiedzi: {e}")
        return False


def login(page):
    print("[INFO] Otwieram stronę logowania...")

    page.goto(
        "https://lingos.pl/h/login",
        wait_until="domcontentloaded",
        timeout=60000,
    )

    time.sleep(2)

    # Akceptacja cookies, jeśli się pojawi.
    try:
        cookie_buttons = [
            "Akceptuję",
            "Akceptuj",
            "Zgadzam się",
            "Accept",
            "Allow all",
        ]

        for text in cookie_buttons:
            loc = page.get_by_text(text, exact=True)

            if visible(loc):
                try:
                    loc.click()
                    time.sleep(1)
                    break
                except Exception:
                    pass
    except Exception:
        pass

    # Login.
    inputs = page.locator("input")

    visible_inputs = []

    for i in range(inputs.count()):
        el = inputs.nth(i)

        try:
            if el.is_visible():
                visible_inputs.append(el)
        except Exception:
            pass

    if len(visible_inputs) < 2:
        print("[ERROR] Nie znaleziono pól logowania.")
        print_page_state(page, "[LOGIN] ")
        return False

    try:
        visible_inputs[0].fill(USERNAME)
        visible_inputs[1].fill(PASSWORD)
    except Exception as e:
        print(f"[ERROR] Nie można wpisać danych logowania: {e}")
        return False

    # Szukamy przycisku logowania.
    login_button = None

    selectors = [
        "button:has-text('Zaloguj')",
        "button:has-text('Zaloguj się')",
        "input[type='submit']",
        "button[type='submit']",
    ]

    for selector in selectors:
        try:
            loc = page.locator(selector)

            for i in range(loc.count()):
                el = loc.nth(i)

                if el.is_visible():
                    login_button = el
                    break

            if login_button:
                break

        except Exception:
            pass

    if not login_button:
        print("[ERROR] Nie znaleziono przycisku logowania.")
        print_page_state(page, "[LOGIN] ")
        return False

    try:
        login_button.click()

        page.wait_for_load_state(
            "domcontentloaded",
            timeout=30000,
        )

    except Exception:
        pass

    time.sleep(3)

    print(f"[INFO] URL po logowaniu: {page.url}")

    return True


def open_learning(page):
    print("[INFO] Szukam sekcji 'Ucz się'...")

    # Najpierw próbujemy kliknąć "Ucz się".
    selectors = [
        "text=Ucz się",
        "a:has-text('Ucz się')",
        "button:has-text('Ucz się')",
    ]

    for selector in selectors:
        try:
            loc = page.locator(selector)

            for i in range(loc.count()):
                el = loc.nth(i)

                if not el.is_visible():
                    continue

                try:
                    el.click()
                    time.sleep(3)

                    print(f"[INFO] URL nauki: {page.url}")

                    if "learning" in page.url:
                        return True

                except Exception:
                    pass

        except Exception:
            pass

    # Awaryjnie bezpośredni adres.
    try:
        page.goto(
            "https://lingos.pl/learning",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        time.sleep(3)

        print(f"[INFO] URL nauki: {page.url}")

        return "learning" in page.url

    except Exception as e:
        print(f"[ERROR] Nie można otworzyć nauki: {e}")
        return False


def run():
    if not USERNAME or not PASSWORD:
        print("[ERROR] Brak LINGOS_USER lub LINGOS_PASS.")
        sys.exit(1)

    dictionary = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 900,
            }
        )

        try:
            # =========================
            # LOGOWANIE
            # =========================

            if not login(page):
                sys.exit(1)

            # =========================
            # OTWIERANIE NAUKI
            # =========================

            if not open_learning(page):
                print("[ERROR] Nie udało się wejść do nauki.")
                screenshot(page, "learning_error")
                sys.exit(1)

            print("[INFO] Rozpoczynam naukę...")

            # =========================
            # PĘTLA NAUKI
            # =========================

            last_prompt = ""
            same_prompt_count = 0

            for round_number in range(1, MAX_ROUNDS + 1):

                time.sleep(0.5)

                # -------------------------
                # KONIEC LEKCJI
                # -------------------------

                if is_completion_screen(page):
                    print("[OK] Wykryto zakończenie nauki.")
                    break

                # -------------------------
                # 1. EKRAN WPISYWANIA
                # -------------------------
                #
                # TO MUSI BYĆ SPRAWDZANE PRZED "DALEJ".
                #
                # Na ekranie Lingos może jednocześnie istnieć:
                # - input "Twoja odpowiedź"
                # - przycisk "Dalej"
                #
                # Input ma pierwszeństwo.
                # -------------------------

                text_input = find_text_input(page)

                if text_input:
                    print(f"\n[{round_number}] EKRAN ODPOWIEDZI")

                    prompt = extract_prompt(page)

                    print(
                        f"[{round_number}] Aktualne słowo: "
                        f"'{prompt}'"
                    )

                    if not prompt:
                        print(
                            "[WARN] Nie udało się wyciągnąć "
                            "słowa z ekranu."
                        )

                        print_page_state(
                            page,
                            f"[{round_number}] ",
                        )

                        screenshot(
                            page,
                            f"debug_answer_{round_number}",
                        )

                        # Nie wpisujemy pustej odpowiedzi, jeśli
                        # nawet nie wiemy, jakie jest słowo.
                        time.sleep(1)
                        continue

                    prompt_key = normalize_text(prompt).lower()

                    # -------------------------
                    # OCHRONA PRZED BŁĘDNYM PARSEREM
                    # -------------------------

                    if (
                        "przetłumacz" in prompt_key
                        or "błędna odpowiedź" in prompt_key
                        or "dalej" in prompt_key
                        or "[enter]" in prompt_key
                    ):
                        print(
                            "[WARN] Parser zwrócił nieprawidłowy "
                            "tekst jako słowo:"
                        )
                        print(f"[WARN] '{prompt}'")

                        screenshot(
                            page,
                            f"bad_prompt_{round_number}",
                        )

                        time.sleep(1)
                        continue

                    # -------------------------
                    # SPRAWDZAMY SŁOWNIK
                    # -------------------------

                    if prompt_key in dictionary:
                        answer = dictionary[prompt_key]

                        print(
                            f"[INFO] Znam odpowiedź: "
                            f"'{answer}'"
                        )

                    else:
                        answer = ""

                        print(
                            "[INFO] Nie znam jeszcze odpowiedzi."
                        )

                    # -------------------------
                    # ZAPISUJEMY AKTUALNE SŁOWO
                    # -------------------------

                    if prompt_key == last_prompt:
                        same_prompt_count += 1
                    else:
                        same_prompt_count = 0
                        last_prompt = prompt_key

                    # -------------------------
                    # WPISANIE ODPOWIEDZI
                    # -------------------------

                    if not submit_answer(
                        page,
                        text_input,
                        answer,
                    ):
                        print(
                            "[ERROR] Nie udało się "
                            "wysłać odpowiedzi."
                        )
                        time.sleep(1)
                        continue

                    time.sleep(1)

                    continue

                # -------------------------
                # 2. EKRAN Z WYNIKIEM
                # -------------------------

                if is_result_screen(page):
                    print(
                        f"\n[{round_number}] "
                        "EKRAN Z WYNIKIEM"
                    )

                    result_prompt, correct_answer = (
                        extract_result_answer(page)
                    )

                    print(
                        f"[INFO] Wykryte słowo: "
                        f"'{result_prompt}'"
                    )

                    print(
                        f"[INFO] Poprawna odpowiedź: "
                        f"'{correct_answer}'"
                    )

                    if result_prompt and correct_answer:

                        key = normalize_text(
                            result_prompt
                        ).lower()

                        answer = normalize_text(
                            correct_answer
                        )

                        dictionary[key] = answer

                        print(
                            f"[ZAPAMIĘTANO] "
                            f"'{result_prompt}' -> "
                            f"'{answer}'"
                        )

                    else:
                        print(
                            "[WARN] Nie udało się "
                            "wyciągnąć poprawnej odpowiedzi."
                        )

                        print(
                            "[DEBUG] Treść strony:"
                        )
                        print(body_text(page)[:3000])

                    if not click_next_and_wait(page):
                        time.sleep(1)

                    continue

                # -------------------------
                # 3. EKRAN Z "DALEJ"
                # -------------------------

                next_button = find_next_button(page)

                if next_button:
                    print(
                        f"\n[{round_number}] "
                        "EKRAN Z PRZYCISKIEM 'DALEJ'."
                    )

                    # Jeśli jesteśmy tutaj, NIE ma inputa.
                    # Czyli jest to ekran po odpowiedzi.

                    result_prompt, correct_answer = (
                        extract_result_answer(page)
                    )

                    if result_prompt and correct_answer:
                        key = normalize_text(
                            result_prompt
                        ).lower()

                        answer = normalize_text(
                            correct_answer
                        )

                        dictionary[key] = answer

                        print(
                            f"[ZAPAMIĘTANO] "
                            f"'{result_prompt}' -> "
                            f"'{answer}'"
                        )
                    else:
                        print(
                            "[INFO] Nie udało się "
                            "wyciągnąć wyniku z ekranu."
                        )

                    if not click_next_and_wait(page):
                        time.sleep(1)

                    continue

                # -------------------------
                # 4. NIEZNANY EKRAN
                # -------------------------

                print(
                    f"\n[{round_number}] "
                    "NIEZNANY EKRAN"
                )

                print_page_state(
                    page,
                    f"[{round_number}] ",
                )

                print(
                    "[DEBUG] Fragment strony:"
                )
                print(body_text(page)[:2500])

                screenshot(
                    page,
                    f"unknown_{round_number}",
                )

                time.sleep(2)

            else:
                print(
                    f"[WARN] Osiągnięto limit "
                    f"{MAX_ROUNDS} rund."
                )

            print()
            print(
                f"[INFO] Zapamiętanych słów: "
                f"{len(dictionary)}"
            )

            for key, value in dictionary.items():
                print(
                    f"  {key} -> {value}"
                )

            print("[OK] Bot zakończył działanie.")

        except Exception as e:
            print(f"[FATAL] {type(e).__name__}: {e}")

            try:
                screenshot(page, "fatal_error")
            except Exception:
                pass

            raise

        finally:
            browser.close()


if __name__ == "__main__":
    run()