import os
import sys
import time
import re

from playwright.sync_api import sync_playwright


USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

MAX_ROUNDS = 300


# ============================================================
# PODSTAWOWE FUNKCJE
# ============================================================

def normalize(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def body_text(page):
    try:
        return normalize(
            page.locator("body").inner_text(timeout=5000)
        )
    except Exception:
        return ""


def screenshot(page, name):
    try:
        page.screenshot(
            path=f"{name}.png",
            full_page=True
        )
    except Exception:
        pass


def is_visible_enabled(locator):
    try:
        return (
            locator.is_visible()
            and locator.is_enabled()
        )
    except Exception:
        return False


# ============================================================
# DEBUG
# ============================================================

def print_page_state(page, prefix=""):
    print(
        f"{prefix}URL: {page.url}"
    )

    try:
        buttons = page.locator("button")

        result = []

        for i in range(buttons.count()):

            el = buttons.nth(i)

            try:
                if el.is_visible():

                    txt = normalize(
                        el.inner_text()
                    )

                    if txt:
                        result.append(txt)

            except Exception:
                pass

        print(
            f"{prefix}PRZYCISKI: {result}"
        )

    except Exception:
        pass

    try:
        inputs = page.locator("input")

        result = []

        for i in range(inputs.count()):

            el = inputs.nth(i)

            try:

                if el.is_visible():

                    result.append(
                        f"type={el.get_attribute('type')} "
                        f"name={el.get_attribute('name')} "
                        f"placeholder={el.get_attribute('placeholder')} "
                        f"id={el.get_attribute('id')}"
                    )

            except Exception:
                pass

        print(
            f"{prefix}INPUTY: {result}"
        )

    except Exception:
        pass


# ============================================================
# COOKIES
# ============================================================

def accept_cookies(page):

    try:

        cookie_buttons = [
            "Akceptuję",
            "Akceptuj",
            "Zgadzam się",
            "Accept",
            "Allow all",
        ]

        for text in cookie_buttons:

            try:

                loc = page.get_by_text(
                    text,
                    exact=True
                )

                for i in range(loc.count()):

                    el = loc.nth(i)

                    if not is_visible_enabled(el):
                        continue

                    print(
                        f"[INFO] Akceptuję cookies: {text}"
                    )

                    el.click()

                    time.sleep(1)

                    return

            except Exception:
                pass

    except Exception:
        pass


# ============================================================
# LOGOWANIE
# ============================================================

def find_login_fields(page):

    username_input = None
    password_input = None

    # --------------------------------------------------------
    # HASŁO
    # --------------------------------------------------------

    try:

        loc = page.locator(
            "input[type='password']"
        )

        for i in range(loc.count()):

            el = loc.nth(i)

            if is_visible_enabled(el):

                password_input = el
                break

    except Exception:
        pass

    # --------------------------------------------------------
    # LOGIN / EMAIL
    #
    # UWAGA:
    # Nie bierzemy wszystkich inputów,
    # bo Cookiebot ma własne checkboxy.
    # --------------------------------------------------------

    try:

        loc = page.locator(
            "input:not([type='checkbox']):not([type='hidden']):not([type='password'])"
        )

        # Najpierw szukamy po nazwach.

        for i in range(loc.count()):

            el = loc.nth(i)

            if not is_visible_enabled(el):
                continue

            input_type = (
                el.get_attribute("type")
                or "text"
            ).lower()

            name = (
                el.get_attribute("name")
                or ""
            ).lower()

            placeholder = (
                el.get_attribute("placeholder")
                or ""
            ).lower()

            element_id = (
                el.get_attribute("id")
                or ""
            ).lower()

            if input_type in (
                "submit",
                "button",
                "reset",
            ):
                continue

            combined = (
                name
                + " "
                + placeholder
                + " "
                + element_id
            )

            if any(
                word in combined
                for word in [
                    "email",
                    "login",
                    "user",
                    "username",
                    "uzytkownik",
                    "użytkownik",
                ]
            ):

                username_input = el
                break

        # ----------------------------------------------------
        # AWARYJNIE:
        # pierwszy edytowalny text/email
        # ----------------------------------------------------

        if username_input is None:

            for i in range(loc.count()):

                el = loc.nth(i)

                if not is_visible_enabled(el):
                    continue

                input_type = (
                    el.get_attribute("type")
                    or "text"
                ).lower()

                if input_type in (
                    "",
                    "text",
                    "email",
                ):

                    username_input = el
                    break

    except Exception:
        pass

    return (
        username_input,
        password_input
    )


def find_login_button(page):

    selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Zaloguj się')",
        "button:has-text('Zaloguj')",
    ]

    for selector in selectors:

        try:

            loc = page.locator(
                selector
            )

            for i in range(loc.count()):

                el = loc.nth(i)

                if is_visible_enabled(el):

                    return el

        except Exception:
            pass

    return None


def login(page):

    print(
        "[INFO] Otwieram stronę logowania..."
    )

    try:

        page.goto(
            "https://lingos.pl/h/login",
            wait_until="domcontentloaded",
            timeout=60000
        )

    except Exception as e:

        print(
            f"[ERROR] Nie można otworzyć logowania: {e}"
        )

        return False

    time.sleep(2)

    accept_cookies(page)

    username_input, password_input = find_login_fields(
        page
    )

    if (
        username_input is None
        or password_input is None
    ):

        print(
            "[ERROR] Nie znaleziono pól logowania."
        )

        print_page_state(
            page,
            "[LOGIN] "
        )

        screenshot(
            page,
            "login_fields_error"
        )

        return False

    print(
        "[INFO] Znaleziono pola logowania."
    )

    # --------------------------------------------------------
    # WPISYWANIE
    # --------------------------------------------------------

    try:

        username_input.fill(
            USERNAME
        )

        password_input.fill(
            PASSWORD
        )

    except Exception as e:

        print(
            f"[ERROR] Nie można wpisać danych: {e}"
        )

        return False

    # --------------------------------------------------------
    # LOGOWANIE
    # --------------------------------------------------------

    login_button = find_login_button(
        page
    )

    try:

        if login_button:

            print(
                "[INFO] Klikam przycisk logowania..."
            )

            login_button.click()

        else:

            print(
                "[INFO] Nie znaleziono przycisku."
            )

            print(
                "[INFO] Wysyłam formularz klawiszem Enter..."
            )

            password_input.press(
                "Enter"
            )

    except Exception as e:

        print(
            f"[WARN] Problem przy wysyłaniu formularza: {e}"
        )

        try:
            password_input.press("Enter")
        except Exception:
            pass

    # --------------------------------------------------------
    # CZEKAMY NA REAKCJĘ
    # --------------------------------------------------------

    for _ in range(30):

        time.sleep(1)

        current_url = page.url.lower()

        if "/h/login" not in current_url:

            print(
                f"[OK] Logowanie zakończone."
            )

            print(
                f"[INFO] URL po logowaniu: {page.url}"
            )

            return True

    # --------------------------------------------------------
    # NADAL LOGIN
    # --------------------------------------------------------

    print(
        f"[ERROR] Nadal jesteśmy na stronie logowania:"
    )

    print(
        page.url
    )

    print(
        "[ERROR] Logowanie nie zostało potwierdzone."
    )

    print_page_state(
        page,
        "[LOGIN] "
    )

    print(
        "[DEBUG] Fragment strony:"
    )

    print(
        body_text(page)[:3000]
    )

    screenshot(
        page,
        "login_failed"
    )

    return False


# ============================================================
# ZNALEZIENIE AKTUALNEJ LEKCJI
# ============================================================

def find_learning_link(page):

    print(
        "[INFO] Szukam aktualnego linku do nauki..."
    )

    # --------------------------------------------------------
    # Najpierw sprawdzamy wszystkie linki.
    # Nie używamy żadnego konkretnego groupId.
    # --------------------------------------------------------

    try:

        links = page.locator(
            "a[href]"
        )

        candidates = []

        for i in range(links.count()):

            el = links.nth(i)

            try:

                if not el.is_visible():
                    continue

                href = (
                    el.get_attribute("href")
                    or ""
                )

                text = normalize(
                    el.inner_text()
                )

                if not href:
                    continue

                full = href.lower()

                # Interesują nas tylko ścieżki związane
                # z nauką.

                if (
                    "/learning/" in full
                    or "/learn/" in full
                ):

                    candidates.append(
                        (
                            href,
                            text
                        )
                    )

            except Exception:
                pass

        print(
            f"[INFO] Znaleziono kandydatów: "
            f"{len(candidates)}"
        )

        # ----------------------------------------------------
        # Preferujemy start lekcji.
        # ----------------------------------------------------

        for href, text in candidates:

            if "/learning/start/" in href.lower():

                print(
                    f"[OK] Znaleziono aktualną lekcję:"
                )

                print(
                    f"[INFO] {href}"
                )

                return href

        # ----------------------------------------------------
        # Jeśli nie ma /learning/start/
        # używamy pierwszego linku do learning.
        # ----------------------------------------------------

        if candidates:

            href, text = candidates[0]

            print(
                f"[OK] Znaleziono link do nauki:"
            )

            print(
                f"[INFO] {href}"
            )

            return href

    except Exception as e:

        print(
            f"[WARN] Błąd szukania linków: {e}"
        )

    return None


# ============================================================
# WEJŚCIE DO NAUKI
# ============================================================

def open_learning(page):

    # --------------------------------------------------------
    # Nie ma tutaj żadnego stałego linku do lekcji.
    # --------------------------------------------------------

    link = find_learning_link(
        page
    )

    if link:

        try:

            print(
                "[INFO] Przechodzę do aktualnej lekcji..."
            )

            # Jeśli href jest względny,
            # klikamy element zamiast ręcznie budować URL.

            links = page.locator(
                f"a[href='{link}']"
            )

            clicked = False

            for i in range(links.count()):

                el = links.nth(i)

                if is_visible_enabled(el):

                    el.click()

                    clicked = True

                    break

            if not clicked:

                # Fallback dla względnego/bezwzględnego href.

                if link.startswith("/"):
                    target = (
                        "https://lingos.pl"
                        + link
                    )
                else:
                    target = link

                page.goto(
                    target,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

            time.sleep(3)

            if "/learning/" in page.url.lower():

                print(
                    f"[OK] Jesteśmy w nauce: {page.url}"
                )

                return True

        except Exception as e:

            print(
                f"[WARN] Nie udało się wejść "
                f"w znaleziony link: {e}"
            )

    # --------------------------------------------------------
    # Jeśli linku nie ma, szukamy przycisku/tekstu.
    # --------------------------------------------------------

    selectors = [
        "text=Ucz się",
        "text=Nauka",
        "text=Rozpocznij",
        "text=Kontynuuj",
    ]

    for selector in selectors:

        try:

            loc = page.locator(
                selector
            )

            for i in range(loc.count()):

                el = loc.nth(i)

                if not is_visible_enabled(el):
                    continue

                print(
                    f"[INFO] Próbuję wejść przez: "
                    f"{selector}"
                )

                el.click()

                time.sleep(3)

                if "/learning/" in page.url.lower():

                    print(
                        f"[OK] Jesteśmy w nauce: {page.url}"
                    )

                    return True

        except Exception:
            pass

    # --------------------------------------------------------
    # Ostatnia próba:
    # przechodzimy na stronę główną po zalogowaniu
    # i ponownie szukamy linków.
    # --------------------------------------------------------

    try:

        print(
            "[INFO] Nie znaleziono lekcji."
        )

        print(
            "[INFO] Odświeżam aktualną stronę..."
        )

        page.reload(
            wait_until="domcontentloaded",
            timeout=60000
        )

        time.sleep(2)

        link = find_learning_link(
            page
        )

        if link:

            try:

                if link.startswith("/"):
                    target = (
                        "https://lingos.pl"
                        + link
                    )
                else:
                    target = link

                page.goto(
                    target,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                time.sleep(2)

                if "/learning/" in page.url.lower():

                    print(
                        f"[OK] Jesteśmy w nauce: {page.url}"
                    )

                    return True

            except Exception:
                pass

    except Exception:
        pass

    print(
        "[ERROR] Nie udało się znaleźć aktualnej lekcji."
    )

    print_page_state(
        page,
        "[LEARNING] "
    )

    print(
        "[DEBUG] Fragment strony:"
    )

    print(
        body_text(page)[:4000]
    )

    screenshot(
        page,
        "learning_not_found"
    )

    return False


# ============================================================
# WYCIĄGANIE AKTUALNEGO SŁOWA
# ============================================================

def extract_prompt(page):

    text = body_text(
        page
    )

    if not text:
        return ""

    # --------------------------------------------------------
    # Przykład:
    #
    # 0/20 PRZETŁUMACZ wpaść do kogoś Dalej [Enter]
    # --------------------------------------------------------

    match = re.search(
        r"PRZETŁUMACZ\s+(.+?)(?:\s+Dalej(?:\s+\[Enter\])?|$)",
        text,
        re.IGNORECASE
    )

    if match:

        result = normalize(
            match.group(1)
        )

        if result:

            return result

    return ""


# ============================================================
# POPRAWNA ODPOWIEDŹ
# ============================================================

def extract_correct_answer(
    page,
    previous_prompt
):

    if not previous_prompt:
        return "", ""

    text = body_text(
        page
    )

    if not text:
        return "", ""

    prompt = normalize(
        previous_prompt
    )

    try:

        pattern = (
            re.escape(prompt)
            + r"\s+(.+?)"
            r"(?:\s+Dalej(?:\s+\[Enter\])?|$)"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            answer = normalize(
                match.group(1)
            )

            if answer:

                return (
                    prompt,
                    answer
                )

    except Exception:
        pass

    return "", ""


# ============================================================
# EKRAN ODPOWIEDZI
# ============================================================

def is_answer_screen(page):

    return (
        find_answer_input(page)
        is not None
    )


# ============================================================
# WYSŁANIE ODPOWIEDZI
# ============================================================

def submit_answer(
    page,
    input_element,
    answer
):

    try:

        input_element.click()

        input_element.fill(
            answer
        )

        print(
            f"[INFO] Wpisuję odpowiedź: "
            f"'{answer}'"
        )

        input_element.press(
            "Enter"
        )

        time.sleep(1)

        return True

    except Exception as e:

        print(
            f"[ERROR] Nie można wysłać odpowiedzi: {e}"
        )

        return False


# ============================================================
# KLIKNIĘCIE DALEJ
# ============================================================

def click_next(page):

    button = find_next_button(
        page
    )

    if not button:
        return False

    try:

        button.click()

        time.sleep(1)

        return True

    except Exception as e:

        print(
            f"[ERROR] Nie można kliknąć Dalej: {e}"
        )

        return False


# ============================================================
# CZY KONIEC
# ============================================================

def is_finished(page):

    text = body_text(
        page
    ).lower()

    markers = [
        "ukończono",
        "gratulacje",
        "zakończono",
        "lekcja zakończona",
    ]

    return any(
        marker in text
        for marker in markers
    )


# ============================================================
# GŁÓWNY BOT
# ============================================================

def run():

    if not USERNAME:

        print(
            "[ERROR] Brak LINGOS_USER."
        )

        sys.exit(1)

    if not PASSWORD:

        print(
            "[ERROR] Brak LINGOS_PASS."
        )

        sys.exit(1)

    dictionary = {}

    last_prompt = ""

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 900
            }
        )

        try:

            # ==================================================
            # LOGIN
            # ==================================================

            if not login(page):

                print(
                    "[FATAL] Nie udało się zalogować."
                )

                sys.exit(1)

            # ==================================================
            # AKTUALNA LEKCJA
            # ==================================================

            if not open_learning(page):

                print(
                    "[FATAL] Nie udało się znaleźć "
                    "aktualnej lekcji."
                )

                sys.exit(1)

            # ==================================================
            # NAUKA
            # ==================================================

            print(
                "[INFO] Rozpoczynam naukę..."
            )

            for round_number in range(
                1,
                MAX_ROUNDS + 1
            ):

                time.sleep(0.5)

                # ------------------------------------------------
                # KONIEC
                # ------------------------------------------------

                if is_finished(page):

                    print(
                        "[OK] Lekcja zakończona."
                    )

                    break

                # ------------------------------------------------
                # INPUT ODPOWIEDZI
                #
                # TO MA PIERWSZEŃSTWO NAD "DALEJ"
                # ------------------------------------------------

                answer_input = find_answer_input(
                    page
                )

                if answer_input:

                    prompt = extract_prompt(
                        page
                    )

                    print()
                    print(
                        f"[{round_number}] "
                        f"Aktualne słowo: "
                        f"'{prompt}'"
                    )

                    if not prompt:

                        print(
                            "[WARN] Nie znaleziono słowa."
                        )

                        print(
                            body_text(page)[:2500]
                        )

                        screenshot(
                            page,
                            f"unknown_prompt_{round_number}"
                        )

                        time.sleep(1)

                        continue

                    last_prompt = prompt

                    key = normalize(
                        prompt
                    ).lower()

                    # ------------------------------------------------
                    # ZNAMY ODPOWIEDŹ
                    # ------------------------------------------------

                    if key in dictionary:

                        answer = dictionary[key]

                        print(
                            f"[INFO] Z pamięci: "
                            f"'{answer}'"
                        )

                    else:

                        # ------------------------------------------------
                        # Pierwsza próba:
                        # puste pole.
                        #
                        # Lingos pokaże poprawną odpowiedź.
                        # ------------------------------------------------

                        answer = ""

                        print(
                            "[INFO] Brak odpowiedzi w pamięci."
                        )

                    submit_answer(
                        page,
                        answer_input,
                        answer
                    )

                    continue

                # ------------------------------------------------
                # EKRAN PO ODPOWIEDZI
                # ------------------------------------------------

                if last_prompt:

                    result_prompt, correct_answer = (
                        extract_correct_answer(
                            page,
                            last_prompt
                        )
                    )

                    if (
                        result_prompt
                        and correct_answer
                    ):

                        key = normalize(
                            result_prompt
                        ).lower()

                        answer = normalize(
                            correct_answer
                        )

                        dictionary[key] = answer

                        print(
                            f"[ZAPAMIĘTANO] "
                            f"'{result_prompt}' -> "
                            f"'{answer}'"
                        )

                        last_prompt = result_prompt

                # ------------------------------------------------
                # DALEJ
                # ------------------------------------------------

                if click_next(page):

                    continue

                # ------------------------------------------------
                # NIEZNANY EKRAN
                # ------------------------------------------------

                print(
                    f"[{round_number}] "
                    "Nie rozpoznano ekranu."
                )

                print_page_state(
                    page,
                    "[DEBUG] "
                )

                print(
                    "[DEBUG] Treść strony:"
                )

                print(
                    body_text(page)[:3000]
                )

                screenshot(
                    page,
                    f"unknown_screen_{round_number}"
                )

                time.sleep(2)

            print()
            print(
                f"[INFO] Zapamiętanych słów: "
                f"{len(dictionary)}"
            )

            print(
                "[OK] Bot zakończył działanie."
            )

        except Exception as e:

            print()
            print(
                f"[FATAL] {type(e).__name__}: {e}"
            )

            screenshot(
                page,
                "fatal_error"
            )

            raise

        finally:

            browser.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    run()