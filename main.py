import os
import time
import random
import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pl-PL,pl;q=0.9"
})

# 1. Logowanie
login_url = "https://lingos.pl/h/login"
res = session.get(login_url)
soup = BeautifulSoup(res.text, 'html.parser')

token_input = soup.find('input', {'name': '_token'})
token = token_input.get('value', '') if token_input else ''

payload = {
    'login': USERNAME,
    'email': USERNAME,
    'password': PASSWORD,
    '_token': token
}

post_res = session.post(login_url, data=payload)

if "Wyloguj" not in post_res.text and "Moje grupy" not in post_res.text and post_res.status_code != 200:
    print("Błąd logowania!")
    exit(1)

print("Zalogowano pomyślnie. Rozpoczynam automatyczne rozwiązywanie słówek...")

# 2. Pętla rozwiązywania lekcji
dictionary = {}
group_url = "https://lingos.pl/students/group"

for step in range(80):
    page = session.get(group_url)
    soup = BeautifulSoup(page.text, 'html.parser')

    if "Koniec lekcji" in page.text or "Brak słówek" in page.text or "Gratulacje" in page.text:
        print("Lekcja została w pełni ukończona!")
        break

    form = soup.find('form')
    if not form:
        print("Nie znaleziono więcej słówek do przerobienia.")
        break

    action_url = form.get('action') or group_url
    if not action_url.startswith("http"):
        action_url = "https://lingos.pl" + action_url

    form_data = {}
    for inp in form.find_all('input'):
        name = inp.get('name')
        val = inp.get('value', '')
        if name:
            form_data[name] = val

    word_element = soup.find('div', {'class': 'word-to-translate'}) or soup.find('h3') or soup.find('strong')
    word_text = word_element.text.strip() if word_element else "słówko"

    correct_ans_element = soup.find('span', {'class': 'correct-answer'}) or soup.find('div', {'class': 'alert-success'})
    if correct_ans_element:
        dictionary[word_text] = correct_ans_element.text.strip()

    answer = dictionary.get(word_text, "")

    answer_input_name = 'answer'
    for inp in form.find_all('input'):
        if inp.get('type') == 'text' or 'ans' in inp.get('name', ''):
            answer_input_name = inp.get('name')
            break

    form_data[answer_input_name] = answer

    wait_time = random.randint(3, 5)
    print(f"[{step+1}] Odpowiadam na '{word_text}' -> '{answer}' | Czekam {wait_time}s...")
    time.sleep(wait_time)

    session.post(action_url, data=form_data)

print("Sesja zakończona sukcesem!")
