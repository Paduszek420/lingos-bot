import os
import time
import random
import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

if not USERNAME or not PASSWORD:
    print("[X] BŁĄD: Brak danych logowania w Secrets!")
    exit(1)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8"
})

LOGIN_URL = "https://lingos.pl/h/login"
START_URL = "https://lingos.pl/learning/start/0?groupId=19788"

try:
    print("1. Pobieranie formularza logowania...")
    res = session.get(LOGIN_URL)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    form = soup.find('form')
    payload = {}
    
    if form:
        for inp in form.find_all('input'):
            name = inp.get('name')
            val = inp.get('value', '')
            if name:
                payload[name] = val
    
    payload['login'] = USERNAME
    payload['password'] = PASSWORD
    
    if '_token' not in payload or not payload['_token']:
        meta_token = soup.find('meta', {'name': 'csrf-token'}) or soup.find('meta', {'name': '_token'})
        if meta_token:
            payload['_token'] = meta_token.get('content', '')

    print("2. Logowanie do konta...")
    action_url = form.get('action') if form and form.get('action') else LOGIN_URL
    if not action_url.startswith("http"):
        action_url = "https://lingos.pl" + action_url

    post_res = session.post(action_url, data=payload)

    if post_res.status_code == 400:
        print("[X] BŁĄD 400: Odrzucono logowanie.")
        exit(1)

    print("[OK] Zalogowano! Przechodzę do rozwiązywania lekcji...")
    
    current_url = START_URL
    dictionary = {}
    
    # Lista fraz kończących lekcję (dopasowana do Twojego ekranu)
    END_PHRASES = [
        "koniec lekcji", 
        "gratulacje", 
        "brak słówek", 
        "podsumowanie", 
        "lekcja wykonana", 
        "dzisiaj powtórzone", 
        "tak trzymaj",
        "przerób jeszcze"
    ]
    
    for step in range(100):
        page = session.get(current_url)
        soup = BeautifulSoup(page.text, 'html.parser')
        
        page_text = page.text.lower()
        if any(term in page_text for term in END_PHRASES):
            print("[+] Wykryto ekran końcowy: Lekcja została w pełni ukończona!")
            break
            
        step_form = soup.find('form')
        if not step_form:
            print("[!] Brak formularza na stronie – koniec lekcji.")
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
        
        wait = random.randint(3, 5)
        print(f"[{step+1}] Słówko: '{word_text}' | Odpowiedź: '{answer}' | Czekam {wait}s...")
        time.sleep(wait)
        
        p_res = session.post(step_action, data=step_data)
        if p_res.url:
            current_url = p_res.url

    print("=== SUCCESS: LEKCJA ZROBIONA ===")

except Exception as e:
    print(f"[X] Wystąpił błąd: {e}")
    exit(1)
