import os
import time
import random
import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

if not USERNAME or not PASSWORD:
    print("[X] BŁĄD: Brak danych logowania w Secrets (LINGOS_USER / LINGOS_PASS)!")
    exit(1)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://lingos.pl/h/login"
})

LOGIN_URL = "https://lingos.pl/h/login"

try:
    print("1. Pobieranie tokenów sesji ze strony logowania...")
    res = session.get(LOGIN_URL, timeout=15)
    soup = BeautifulSoup(res.text, 'html.parser')

    form = soup.find('form')
    if not form:
        print("[X] BŁĄD: Nie znaleziono formularza na stronie logowania.")
        exit(1)

    # Automatyczne zbieranie wszystkich ukrytych pól (tokeny CSRF itp.)
    payload = {}
    for inp in form.find_all('input'):
        name = inp.get('name')
        val = inp.get('value', '')
        if name:
            payload[name] = val

    # Przypisanie loginu i hasła do wykrytych pól
    for key in list(payload.keys()):
        key_lower = key.lower()
        if 'user' in key_lower or 'login' in key_lower or 'email' in key_lower:
            payload[key] = USERNAME
        elif 'pass' in key_lower:
            payload[key] = PASSWORD

    payload['login'] = USERNAME
    payload['email'] = USERNAME
    payload['password'] = PASSWORD

    action_url = form.get('action') or LOGIN_URL
    if not action_url.startswith("http"):
        action_url = "https://lingos.pl" + action_url

    print(f"2. Wysyłanie logowania do: {action_url}...")
    post_res = session.post(action_url, data=payload, timeout=15)

    page_text = post_res.text.lower()
    # Weryfikacja udanego logowania
    if "wyloguj" in page_text or "logout" in page_text or "moje grupy" in page_text or post_res.url != LOGIN_URL:
        print(f"[OK] Zalogowano pomyślnie! URL po logowaniu: {post_res.url}")
    else:
        print("[X] BŁĄD LOGOWANIA: Serwer nie zalogował użytkownika.")
        print(f"URL docelowy: {post_res.url}")
        print("Najczęstsza przyczyna: spacja na początku/końcu loginu lub hasła w Secrets na GitHubie.")
        exit(1)

    # 3. Szukanie linku do lekcji
    start_url = None
    dash_soup = BeautifulSoup(post_res.text, 'html.parser')
    for a in dash_soup.find_all('a', href=True):
        if '/learning/start' in a['href'] or '/start' in a['href']:
            start_url = a['href']
            break

    if not start_url:
        for path in ["/h/student", "/students", "/students/group"]:
            r = session.get("https://lingos.pl" + path, timeout=10)
            s = BeautifulSoup(r.text, 'html.parser')
            for a in s.find_all('a', href=True):
                if '/learning/start' in a['href'] or '/start' in a['href']:
                    start_url = a['href']
                    break
            if start_url:
                break

    current_url = ("https://lingos.pl" + start_url) if start_url and not start_url.startswith("http") else (start_url or post_res.url)
    print(f"Startowanie lekcji pod adresem: {current_url}")

    # 4. Wykonywanie słówek
    solved_count = 0
    dictionary = {}

    for step in range(25):
        page = session.get(current_url, timeout=15)
        soup = BeautifulSoup(page.text, 'html.parser')

        if "koniec lekcji" in page.text.lower() or "gratulacje" in page.text.lower():
            print("[+] Lekcja zakończona!")
            break

        step_form = soup.find('form')
        if not step_form:
            print("[!] Brak formularza ze słówkiem na stronie.")
            break

        step_action = step_form.get('action') or current_url
        if not step_action.startswith("http"):
            step_action = "https://lingos.pl" + step_action

        step_data = {inp.get('name'): inp.get('value', '') for inp in step_form.find_all('input') if inp.get('name')}

        word_el = soup.find('div', {'class': 'word-to-translate'}) or soup.find('h3') or soup.find('strong')
        word_text = word_el.text.strip() if word_el else "słówko"

        correct_el = soup.find('span', {'class': 'correct-answer'}) or soup.find('div', {'class': 'alert-success'})
        if correct_el:
            dictionary[word_text] = correct_el.text.strip()

        answer = dictionary.get(word_text, "")
        ans_name = next((inp.get('name') for inp in step_form.find_all('input') if inp.get('type') == 'text' or 'ans' in inp.get('name', '')), 'answer')
        step_data[ans_name] = answer

        wait = random.randint(2, 4)
        print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Czekam {wait}s...")
        time.sleep(wait)

        p_res = session.post(step_action, data=step_data, timeout=15)
        if p_res.url:
            current_url = p_res.url
        solved_count += 1

    print(f"=== PRZEROBIONO SŁÓWEK: {solved_count} ===")

except Exception as e:
    print(f"[X] Błąd wykonania: {e}")
    exit(1)
