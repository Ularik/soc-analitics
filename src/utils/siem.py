from datetime import datetime
import requests
import urllib3

# Отключаем предупреждения о невалидных SSL-сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://192.168.30.101:10443"

# Данные для входа в SIEM (укажите ваши учетные данные)
USERNAME = "igloosec"
PASSWORD = "Sp!dertm70"

# Создаем сессию, которая автоматически сохраняет Cookies
session = requests.Session()
session.verify = False
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})


def login_and_send():
    # Step 1: Аутентификация в Spring Security
    login_url = f"{BASE_URL}/siem/j_spring_security_check"
    login_payload = {
        "j_username": USERNAME,
        "j_password": PASSWORD
    }

    print("[+] Выполняем вход в SIEM...")
    login_res = session.post(login_url, data=login_payload, timeout=10)

    # Простая проверка: если в ответе снова страница логина, значит пароль неверный
    if "j_spring_security_check" in login_res.text or "Please enter ID" in login_res.text:
        print("[-] Ошибка авторизации: неверный логин или пароль.")
        return

    print("[+] Успешная авторизация. Отправка запроса...")

    # Step 2: Отправка целевого запроса с актуальным временем
    target_url = f"{BASE_URL}/siem/common/get_footer_value.do"
    current_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    target_payload = {
        "footerNoticeTime": current_time,
        "alarmType": "topN"
    }

    target_res = session.post(target_url, data=target_payload, timeout=10)

    print(f"[*] Отправленное время: {current_time}")
    print(f"[*] Статус ответа: {target_res.status_code}")
    print("[*] Ответ сервера:")
    print(target_res.text)


if __name__ == "__main__":
    login_and_send()