import os
import time
import random
import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

if not USERNAME or not PASSWORD:
    print("[X] BŁĄD: Brak danych logowania LINGOS_USER / LINGOS_PASS w Secrets!")
    exit(1)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9"
})

LOGIN_URL = "https://lingos.pl/h/login"

try:
    print("1. Pobieranie formularza logowania...")
    res = session.get(LOGIN_URL, timeout=15)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    form = soup.find('form')
    if not form:
        print("[X] BŁĄD: Nie znaleziono formularza logowania.")
        exit(1)

    payload = {}
    for inp in form.find_all('input'):
        name = inp.get('name')
        val = inp.get('value', '')
        if name:
            payload[name] = val
            
    payload['login'] = USERNAME
    payload['email'] = USERNAME
    payload['password'] = PASSWORD

    action_url = form.get('action') or LOGIN_URL
    if not action_url.startswith("http"):
        action_url = "https://lingos.pl" + action_url

    print(f"2. Logowanie użytkownika '{USERNAME}'...")
    post_res = session.post(action_url, data=payload, timeout=15)

    if "login" in post_res.url.lower() and "wyloguj" not in post_res.text.lower():
        print("[X] BŁĄD LOGOWANIA: Odrzucono dane logowania lub przekierowano do logowania.")
        print("Sprawdź, czy LINGOS_USER i LINGOS_PASS w Secrets są wpisane poprawnie.")
        exit(1)

    print(f"[OK] Zalogowano! Aktualna strona: {post_res.url}")
    
    # 3. Automatyczne wykrywanie linku do lekcji
    start_url = None
    dashboard_soup = BeautifulSoup(post_res.text, 'html.parser')
    
    for a in dashboard_soup.find_all('a', href=True):
        href = a['href']
        if '/learning/start' in href or '/start' in href or 'learning' in href:
            start_url = href
            break

    if not start_url:
        for extra_path in ["/h/student", "/students", "/h/dashboard", "/students/group"]:
            test_res = session.get("https://lingos.pl" + extra_path, timeout=10)
            test_soup = BeautifulSoup(test_res.text, 'html.parser')
            for a in test_soup.find_all('a', href=True):
                if '/learning/start' in a['href'] or '/start' in a['href']:
                    start_url = a['href']
                    break
            if start_url:
                break

    if start_url:
        if not start_url.startswith("http"):
            start_url = "https://lingos.pl" + start_url
        print(f"Znaleziono link do lekcji: {start_url}")
        current_url = start_url
    else:
        print("[!] Nie znaleziono osobnego linku startowego. Używam głównej strony po zalogowaniu.")
        current_url = post_res.url

    # 4. Pętla rozwiązywania lekcji
    solved_count = 0
    dictionary = {}
    
    for step in range(25):
        page = session.get(current_url, timeout=15)
        soup = BeautifulSoup(page.text, 'html.parser')
        
        page_text = page.text.lower()
        if "koniec lekcji" in page_text or "gratulacje" in page_text or "brak słówek" in page_text or "ukończona" in page_text:
            print("[+] Lekcja została ukończona!")
            break
            
        step_form = soup.find('form')
        if not step_form:
            print(f"[!] Brak formularza na stronie: {current_url}")
            break
            
        step_action = step_form.get('action') or current_url
        if not step_action.startswith("http"):
            step_action = "https://lingos.pl" + step_action
            
        step_data = {}
        for inp in step_form.find_all('input'):
            name = inp.get('name')
            val = inp.get('value', '')
            if name:
                step_data[name] = val
                
        word_el = soup.find('div', {'class': 'word-to-translate'}) or soup.find('h3') or soup.find('strong')
        word_text = word_el.text.strip() if word_el else "słówko"
        
        correct_el = soup.find('span', {'class': 'correct-answer'}) or soup.find('div', {'class': 'alert-success'})
        if correct_el:
            dictionary[word_text] = correct_el.text.strip()
            
        answer = dictionary.get(word_text, "")
        
        ans_name = 'answer'
        for inp in step_form.find_all('input'):
            if inp.get('type') == 'text' or 'ans' in inp.get('name', ''):
                ans_name = inp.get('name')
                break
                
        step_data[ans_name] = answer
        
        wait = random.randint(2, 4)
        print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Czekam {wait}s...")
        time.sleep(wait)
        
        p_res = session.post(step_action, data=step_data, timeout=15)
        if p_res.url:
            current_url = p_res.url
        solved_count += 1

    if solved_count == 0:
        print("[X] BŁĄD: Skrypt nie przerobił ani jednego słówka!")
        print("Możliwe powody: lekcja na dziś jest już zrobiona lub brak aktywnych zadań w grupie.")
        exit(1)
        
    print(f"=== SUKCES! PRZEROBIONO SŁÓWEK: {solved_count} ===")

except Exception as e:
    print(f"[X] Wystąpił błąd: {e}")
    exit(1)
