import os
import time
import random
import requests
from bs4 import BeautifulSoup

# Pobieranie danych z GitHub Secrets
USERNAME = os.environ.get("LINGOS_USER", "").strip()
PASSWORD = os.environ.get("LINGOS_PASS", "").strip()

# Adresy ze zdjęcia i dokładnej ścieżki Lingosa
LOGIN_URL = "https://lingos.pl/h/login"
START_URL = "https://lingos.pl/learning/start/0?groupId=19788"

if not USERNAME or not PASSWORD:
    print("[X] BŁĄD: Brak danych logowania w Secrets!")
    exit(1)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pl-PL,pl;q=0.9"
})

try:
    print("=== START BOT LINGOS ===")
    
    # 1. Logowanie
    print(f"Łączenie ze stroną logowania ({LOGIN_URL})...")
    res = session.get(LOGIN_URL)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    token_input = soup.find('input', {'name': '_token'})
    token = token_input.get('value', '') if token_input else ''
    
    payload = {
        'login': USERNAME,
        'email': USERNAME,
        'password': PASSWORD,
        '_token': token
    }
    
    print("Wysyłanie danych logowania...")
    post_res = session.post(LOGIN_URL, data=payload)
    
    if "Wyloguj" not in post_res.text and "logout" not in post_res.text.lower() and "Konto" not in post_res.text:
        print("[X] BŁĄD LOGOWANIA! Sprawdź czy login i hasło w GitHub Secrets są w 100% poprawne.")
        exit(1)
        
    print("[OK] Zalogowano pomyślnie!")
    
    # 2. Uruchomienie konkretnej lekcji
    print(f"Otwieranie lekcji grupy 4F_2026/2027: {START_URL}")
    current_url = START_URL
    dictionary = {}
    
    for step in range(100):
        page = session.get(current_url)
        soup = BeautifulSoup(page.text, 'html.parser')
        
        # Sprawdzanie czy lekcja się skończyła
        page_text_lower = page.text.lower()
        if "koniec lekcji" in page_text_lower or "gratulacje" in page_text_lower or "brak słówek" in page_text_lower or "podsumowanie" in page_text_lower:
            print("[+] Lekcja została w pełni ukończona!")
            break
            
        form = soup.find('form')
        if not form:
            print("[!] Brak formularza na stronie – lekcja dobiegła końca.")
            break
            
        action_url = form.get('action') or current_url
        if not action_url.startswith("http"):
            action_url = "https://lingos.pl" + action_url
            
        form_data = {}
        for inp in form.find_all('input'):
            name = inp.get('name')
            val = inp.get('value', '')
            if name:
                form_data[name] = val
                
        # Odczytywanie słówka
        word_element = soup.find('div', {'class': 'word-to-translate'}) or soup.find('h3') or soup.find('strong') or soup.find('h4')
        word_text = word_element.text.strip() if word_element else "słówko"
        
        # Jeśli pojawiła się poprawna odpowiedź po błędzie
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
        
        # Wysyłanie odpowiedzi
        post_answer = session.post(action_url, data=form_data)
        if post_answer.url:
            current_url = post_answer.url
            
    print("=== SESJA ZAKOŃCZONA SUCCESS ===")

except Exception as e:
    print(f"[X] Wystąpił błąd podczas wykonywania programu: {e}")
    exit(1)
