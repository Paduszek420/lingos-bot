import os
import time
import random
import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("LINGOS_USER")
PASSWORD = os.environ.get("LINGOS_PASS")

if not USERNAME or not PASSWORD:
    print("Błąd: Brak danych logowania w GitHub Secrets!")
    exit(1)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

dictionary = {}

# 1. Logowanie do Lingos.pl
print("Logowanie do Lingos.pl...")
login_url = "https://lingos.pl/h/login"
login_page = session.get(login_url)
soup = BeautifulSoup(login_page.text, 'html.parser')

token_input = soup.find('input', {'name': '_token'})
token = token_input['value'] if token_input else ''

payload = {
    'login': USERNAME,
    'password': PASSWORD,
    '_token': token
}

res = session.post(login_url, data=payload)
if "Wyloguj" not in res.text and "Moje grupy" not in res.text and res.status_code != 200:
    print("Błąd logowania! Sprawdź czy dane w Secrets są poprawne.")
    exit(1)

print("Zalogowano pomyślnie. Rozpoczynam wykonywanie słówek...")

# 2. Pętla rozwiązywania lekcji
group_url = "https://lingos.pl/students/group"

for step in range(80):
    page = session.get(group_url)
    soup = BeautifulSoup(page.text, 'html.parser')

    if "Koniec lekcji" in page.text or "Brak słówek" in page.text or "Gratulacje" in page.text:
        print("Lekcja została w pełni ukończona!")
        break

    form = soup.find('form')
    if not form:
        print("Nie znaleziono formularza słówka lub lekcja dobiegła końca.")
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

    # Odczytywanie słówka i prawidłowej odpowiedzi
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
    print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Czekam {wait_time}s...")
    time.sleep(wait_time)

    session.post(action_url, data=form_data)

print("Zakończono proces.")
