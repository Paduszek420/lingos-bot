import os
import sys
import time
import re

from playwright.sync_api import sync_playwright


USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

MAX_ROUNDS = 300


# ============================================================
# POMOCNICZE
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

    try:
        print(
            f"{prefix}URL: {page.url}"
        )
    except Exception:
        pass

    try:

        buttons = page.locator("button")

        result = []

        for i in range(buttons.count()):

            el = buttons.nth(i)

            try:

                if not el.is_visible():
                    continue

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

                if not el.is_visible():
                    continue

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
# COOKIEBOT
# ============================================================

def accept_cookies(page):

    try:

        # Najpierw sprawdzamy, czy Cookiebot istnieje.

        cookie_dialog = page.locator(
            "#CybotCookiebotDialog"
        )

        if cookie_dialog.count() == 0:
            return

        try:

            if not cookie_dialog.is_visible():
                return

        except Exception:
            return

        print(
            "[INFO] Wykryto okno cookies."
        )

        # ----------------------------------------------------
        # Najczęściej używane przyciski Cookiebot.
        # ----------------------------------------------------

        selectors = [
            "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
            "#CybotCookiebotDialogBodyLevelButtonAccept",
            "#CybotCookiebotDialogBodyButtonAccept",
            "#CybotCookiebotDialogBodyLevelButtonCustomize",
        ]

        for selector in selectors:

            try:

                loc = page.locator(
                    selector
                )

                for i in range(loc.count()):

                    el = loc.nth(i)

                    if not el.is_visible():
                        continue

                    try:

                        el.click(
                            timeout=5000
                        )

                        time.sleep(1)

                        print(
                            "[OK] Obsłużono cookies."
                        )

                        return

                    except Exception:
                        pass

            except Exception:
                pass

        # ----------------------------------------------------
        # Fallback po tekście.
        # ----------------------------------------------------

        texts = [
            "Akceptuję",
            "Akceptuj",
            "Zgadzam się",
            "Accept",
            "Allow all",
        ]

        for text in texts:

            try:

                loc = page.get_by_text(
                    text,
                    exact=True
                )

                for i in range(loc.count()):

                    el = loc.nth(i)

                    if not el.is_visible():
                        continue

                    try:

                        el.click(
                            timeout=5000
                        )

                        time.sleep(1)

                        print(
                            f"[OK] Zaakceptowano cookies: {text}"
                        )

                        return

                    except Exception:
                        pass

            except Exception:
                pass

        # ----------------------------------------------------
        # Jeżeli dialog nadal istnieje, próbujemy kliknąć
        # widoczny przycisk typu "Accept".
        # ----------------------------------------------------

        try:

            buttons = cookie_dialog.locator(
                "button"
            )

            for i in range(buttons.count()):

                el = buttons.nth(i)

                if not el.is_visible():
                    continue

                txt = normalize(
                    el.inner_text()
                ).lower()

                if any(
                    word in txt
                    for word in [
                        "akcept",
                        "zgadzam",
                        "accept",
                        "allow",
                    ]
                ):

                    try:

                        el.click(
                            timeout=5000
                        )

                        time.sleep(1)

                        print(
                            "[OK] Obsłużono Cookiebot."
                        )

                        return

                    except Exception:
                        pass

        except Exception:
            pass

    except Exception:
        pass


def cookies_still_visible(page):

    try:

        dialog = page.locator(
            "#CybotCookiebotDialog"
        )

        return (
            dialog.count() > 0
            and dialog.is_visible()
        )

    except Exception:
        return False


# ============================================================
# POLA LOGOWANIA
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
    # LOGIN
    # --------------------------------------------------------

    try:

        loc = page.locator(
            "input:not([type='checkbox']):not([type='hidden']):not([type='password'])"
        )

        # Najpierw po nazwie / placeholderze / ID.

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

            if input_type in [
                "submit",
                "button",
                "reset",
            ]:
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
        # Fallback.
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

                if input_type in [
                    "",
                    "text",
                    "email",
                ]:

                    username_input = el

                    break

    except Exception:
        pass

    return (
        username_input,
        password_input
    )


# ============================================================
# PRZYCISK LOGOWANIA
# ============================================================

def find_login_button(page):

    selectors = [
        "button#submit-login-button",
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


# ============================================================
# LOGOWANIE
# ============================================================

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

    # --------------------------------------------------------
    # COOKIES
    # --------------------------------------------------------

    accept_cookies(page)

    # Jeżeli Cookiebot nadal zasłania stronę,
    # dajemy mu chwilę.

    if cookies_still_visible(page):

        print(
            "[INFO] Cookiebot nadal widoczny."
        )

        time.sleep(1)

        accept_cookies(page)

    # --------------------------------------------------------
    # POLA
    # --------------------------------------------------------

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
    # COOKIES JESZCZE RAZ
    # --------------------------------------------------------

    accept_cookies(page)

    # --------------------------------------------------------
    # PRZYCISK
    # --------------------------------------------------------

    login_button = find_login_button(
        page
    )

    # --------------------------------------------------------
    # PRÓBA KLIKNIĘCIA
    # --------------------------------------------------------

    if login_button:

        print(
            "[INFO] Klikam przycisk logowania..."
        )

        try:

            login_button.click(
                timeout=5000
            )

        except Exception as e:

            print(
                f"[WARN] Przycisk jest zasłonięty: {e}"
            )

            print(
                "[INFO] Wysyłam formularz klawiszem Enter..."
            )

            try:

                password_input.press(
                    "Enter"
                )

            except Exception as enter_error:

                print(
                    f"[ERROR] Enter nie zadziałał: "
                    f"{enter_error}"
                )

                return False

    else:

        print(
            "[INFO] Brak przycisku — wysyłam Enter."
        )

        try:

            password_input.press(
                "Enter"
            )

        except Exception as e:

            print(
                f"[ERROR] Nie można wysłać formularza: {e}"
            )

            return False

    # --------------------------------------------------------
    # CZEKANIE NA PRZEJŚCIE
    # --------------------------------------------------------

    for _ in range(30):

        time.sleep(1)

        try:
            current_url = page.url.lower()
        except Exception:
            current_url = ""

        if (
            current_url
            and "/h/login" not in current_url
        ):

            print(
                "[OK] Logowanie zakończone."
            )

            print(
                f"[INFO] URL po logowaniu: {page.url}"
            )

            return True

    # --------------------------------------------------------
    # NIE UDAŁO SIĘ
    # --------------------------------------------------------

    print(
        "[ERROR] Logowanie nie zostało potwierdzone."
    )

    print(
        f"[ERROR] Aktualny URL: {page.url}"
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
# AKTUALNY LINK DO NAUKI
# ============================================================

def find_learning_link(page):

    print(
        "[INFO] Szukam aktualnego linku do nauki..."
    )

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

                low = href.lower()

                if (
                    "/learning/" in low
                    or "/learn/" in low
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
        # Preferujemy link startowy.
        # Nadal NIE wpisujemy żadnego konkretnego groupId.
        # ----------------------------------------------------

        for href, text in candidates:

            if "/learning/start/" in href.lower():

                print(
                    "[OK] Znaleziono aktualną lekcję:"
                )

                print(
                    f"[INFO] {href}"
                )

                return href

        # ----------------------------------------------------
        # Dowolny link learning.
        # ----------------------------------------------------

        if candidates:

            href, text = candidates[0]

            print(
                "[OK] Znaleziono link do nauki:"
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
    # Czasami dashboard ładuje się chwilę.
    # --------------------------------------------------------

    time.sleep(2)

    link = find_learning_link(
        page
    )

    if link:

        try:

            # ------------------------------------------------
            # Szukamy konkretnego elementu po href.
            # ------------------------------------------------

            links = page.locator(
                "a[href]"
            )

            clicked = False

            for i in range(links.count()):

                el = links.nth(i)

                try:

                    if not el.is_visible():
                        continue

                    href = (
                        el.get_attribute("href")
                        or ""
                    )

                    if href != link:
                        continue

                    print(
                        "[INFO] Klikam znalezioną lekcję..."
                    )

                    el.click(
                        timeout=10000
                    )

                    clicked = True

                    break

                except Exception:
                    pass

            # ------------------------------------------------
            # Fallback — korzystamy z odnalezionego href.
            #
            # To nadal jest dynamiczny adres znaleziony
            # aktualnie na stronie.
            # ------------------------------------------------

            if not clicked:

                if link.startswith("/"):

                    target = (
                        "https://lingos.pl"
                        + link
                    )

                else:

                    target = link

                print(
                    f"[INFO] Otwieram znaleziony adres: "
                    f"{target}"
                )

                page.goto(
                    target,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

            time.sleep(2)

            if "/learning/" in page.url.lower():

                print(
                    f"[OK] Jesteśmy w nauce: "
                    f"{page.url}"
                )

                return True

        except Exception as e:

            print(
                f"[WARN] Nie udało się wejść "
                f"w znalezioną lekcję: {e}"
            )

    # ========================================================
    # PRÓBA PRZEZ TEKST / PRZYCISK
    # ========================================================

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

                if not el.is_visible():
                    continue

                try:

                    print(
                        f"[INFO] Próbuję: {selector}"
                    )

                    el.click(
                        timeout=10000
                    )

                    time.sleep(2)

                    if "/learning/" in page.url.lower():

                        print(
                            f"[OK] Jesteśmy w nauce: "
                            f"{page.url}"
                        )

                        return True

                except Exception:
                    pass

        except Exception:
            pass

    # ========================================================
    # ODŚWIEŻENIE DASHBOARDU
    # ========================================================

    try:

        print(
            "[INFO] Odświeżam dashboard..."
        )

        page.reload(
            wait_until="domcontentloaded",
            timeout=60000
        )

        time.sleep(3)

        link = find_learning_link(
            page
        )

        if link:

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
                    f"[OK] Jesteśmy w nauce: "
                    f"{page.url}"
                )

                return True

    except Exception as e:

        print(
            f"[WARN] Odświeżenie nie pomogło: {e}"
        )

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
# ODPOWIEDŹ — INPUT
# ============================================================

def find_answer_input(page):

    # --------------------------------------------------------
    # TO JEST WŁAŚNIE FUNKCJA, KTÓREJ BRAKOWAŁO
    # W POPRZEDNIEJ WERSJI.
    # --------------------------------------------------------

    selectors = [
        "input[placeholder='Twoja odpowiedź']",
        "textarea[placeholder='Twoja odpowiedź']",
        "input[placeholder*='Twoja odpowiedź']",
        "textarea[placeholder*='Twoja odpowiedź']",
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

    # --------------------------------------------------------
    # AWARYJNIE
    # --------------------------------------------------------

    selectors = [
        "input[type='text']",
        "textarea",
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

                placeholder = (
                    el.get_attribute("placeholder")
                    or ""
                ).lower()

                if (
                    "odpowied" in placeholder
                    or placeholder == ""
                ):

                    return el

        except Exception:
            pass

    return None


# ============================================================
# AKTUALNE SŁOWO
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
            + r"(?:\s+Dalej(?:\s+\[Enter\])?|$)"
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

                # --------------------------------------------
                # Odcinamy przypadkowe elementy.
                # --------------------------------------------

                answer = re.sub(
                    r"\s*\[Enter\]\s*$",
                    "",
                    answer,
                    flags=re.IGNORECASE
                )

                answer = normalize(
                    answer
                )

                return (
                    prompt,
                    answer
                )

    except Exception:
        pass

    return "", ""


# ============================================================
# DALEJ
# ============================================================

def find_next_button(page):

    selectors = [
        "button:has-text('Dalej')",
        "button:has-text('dalej')",
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


def click_next(page):

    button = find_next_button(
        page
    )

    if not button:
        return False

    try:

        button.click(
            timeout=10000
        )

        time.sleep(0.7)

        return True

    except Exception as e:

        print(
            f"[ERROR] Nie można kliknąć Dalej: {e}"
        )

        return False


# ============================================================
# ODPOWIEDŹ
# ============================================================

def submit_answer(
    page,
    answer_input,
    answer
):

    try:

        answer_input.click(
            timeout=5000
        )

        answer_input.fill(
            answer
        )

        print(
            f"[INFO] Wpisuję odpowiedź: "
            f"'{answer}'"
        )

        answer_input.press(
            "Enter"
        )

        time.sleep(0.8)

        return True

    except Exception as e:

        print(
            f"[ERROR] Nie można wysłać odpowiedzi: "
            f"{e}"
        )

        return False


# ============================================================
# KONIEC
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

    # --------------------------------------------------------
    # SŁOWNIK
    #
    # np.
    # "wpaść do kogoś" -> "come over"
    # --------------------------------------------------------

    dictionary = {}

    # Ostatnie prawdziwe słowo.
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
            # LOGOWANIE
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
                    "[FATAL] Nie znaleziono aktualnej lekcji."
                )

                sys.exit(1)

            # ==================================================
            # START
            # ==================================================

            print(
                "[INFO] Rozpoczynam naukę..."
            )

            # ==================================================
            # PĘTLA
            # ==================================================

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
                        "[OK] Wykryto zakończenie lekcji."
                    )

                    break

                # ------------------------------------------------
                # NAJWAŻNIEJSZE:
                # NAJPIERW SZUKAMY INPUTU.
                #
                # Dzięki temu nie klikamy "Dalej"
                # zanim nie odpowiemy.
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

                    # ------------------------------------------------
                    # Jeśli parser nie znalazł słowa,
                    # nie wysyłamy pustej odpowiedzi bez sensu.
                    # ------------------------------------------------

                    if not prompt:

                        print(
                            "[WARN] Nie znaleziono aktualnego słowa."
                        )

                        print(
                            "[DEBUG]"
                        )

                        print(
                            body_text(page)[:2500]
                        )

                        screenshot(
                            page,
                            f"prompt_error_{round_number}"
                        )

                        time.sleep(1)

                        continue

                    # ------------------------------------------------
                    # Zapamiętujemy słowo.
                    # ------------------------------------------------

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
                            f"[INFO] ZAPAMIĘTANA: "
                            f"'{answer}'"
                        )

                    else:

                        # ------------------------------------------------
                        # Nie znamy.
                        #
                        # Wysyłamy pustą odpowiedź.
                        # Lingos powinien pokazać poprawną.
                        # ------------------------------------------------

                        answer = ""

                        print(
                            "[INFO] Brak odpowiedzi "
                            "w słowniku — sprawdzam poprawną."
                        )

                    submit_answer(
                        page,
                        answer_input,
                        answer
                    )

                    continue

                # ------------------------------------------------
                # NIE MA INPUTU
                #
                # Sprawdzamy, czy Lingos pokazał odpowiedź.
                # ------------------------------------------------

                if last_prompt:

                    (
                        result_prompt,
                        correct_answer
                    ) = extract_correct_answer(
                        page,
                        last_prompt
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

                        # ------------------------------------------------
                        # Zabezpieczenie przed zapisaniem
                        # "Dalej" jako odpowiedzi.
                        # ------------------------------------------------

                        if answer.lower() not in [
                            "dalej",
                            "[enter]",
                        ]:

                            dictionary[key] = answer

                            print(
                                f"[ZAPAMIĘTANO] "
                                f"'{result_prompt}' -> "
                                f"'{answer}'"
                            )

                # ------------------------------------------------
                # DALEJ
                # ------------------------------------------------

                if click_next(page):

                    continue

                # ------------------------------------------------
                # NIEZNANY EKRAN
                # ------------------------------------------------

                print()
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

            # ==================================================
            # KONIEC
            # ==================================================

            print()
            print(
                f"[INFO] Zapamiętanych słów: "
                f"{len(dictionary)}"
            )

            for key, value in dictionary.items():

                print(
                    f"[SŁOWNIK] {key} -> {value}"
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