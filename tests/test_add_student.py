import os
from selenium.webdriver.chrome.options import Options

import pytest
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

BASE_URL = "http://158.160.87.146:5000"
REGISTER_ENDPOINT = f"{BASE_URL}/api/register"
LOGIN_ENDPOINT = f"{BASE_URL}/api/auth"
USERS_PAGE = f"{BASE_URL}/users-page"

@pytest.fixture(scope="session")
def browser():

    use_remote = os.getenv("USE_REMOTE", "false").lower() == "true"

    if use_remote:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.set_capability("browserName", "chrome")
        driver = webdriver.Remote(
            command_executor="http://localhost:4444/wd/hub",
            options=options
        )
    else:
        driver = webdriver.Chrome()

    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def clear_form(browser):
    for field in ["name", "age", "gender", "date_birthday"]:
        el = browser.find_element(By.NAME, field)
        el.clear()
    checkbox = browser.find_element(By.NAME, "is_active")
    if checkbox.is_selected():
        checkbox.click()

def is_error_visible(browser, by, locator, timeout=3):
    try:
        element = WebDriverWait(browser, timeout).until(
            EC.visibility_of_element_located((by, locator))
        )
        return element.is_displayed()
    except TimeoutException:
        return False

def user_exists(token: str, name: str) -> bool:
    response = requests.get(
        "http://localhost:8000/api/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    users = response.json()
    return any(u['name'] == name for u in users)


def token():
    login = "admin_ui"
    password = "pass123"

    # Регистрация через API
    requests.post(REGISTER_ENDPOINT, json={"login": login, "password": password})

    # Авторизация через API
    resp = requests.post(LOGIN_ENDPOINT, json={"login": login, "password": password})
    token = resp.json().get("token")
    return token


@pytest.fixture(scope="session")
def login(browser):
    browser.get(f"{BASE_URL}/login")

    browser.find_element(By.NAME, "login").send_keys("admin_ui")
    browser.find_element(By.NAME, "password").send_keys("pass123")
    browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Ждём, пока появится ссылка на добавление пользователя
    # WebDriverWait(browser, 10).until(
    #     EC.presence_of_element_located((By.LINK_TEXT, "Добавить пользователя"))
    # )
    # go_to_add_student_page(browser)
    WebDriverWait(browser, 5).until(EC.url_to_be(USERS_PAGE))
    WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.LINK_TEXT, "Добавить пользователя"))).click()
    return True


def go_to_add_student_page(browser):
    browser.find_element(By.LINK_TEXT, "Добавить пользователя").click()
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.NAME, "name")))



def fill_and_submit_form(browser, name, age, gender, date_registration, is_active):
    clear_form(browser)
    browser.find_element(By.NAME, "name").send_keys(name)
    browser.find_element(By.NAME, "age").send_keys(age)
    browser.find_element(By.NAME, "gender").send_keys(gender)
    browser.find_element(By.NAME, "date_birthday").send_keys(date_registration)
    if is_active:
        browser.find_element(By.NAME, "is_active").click()
    browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()


# ✅ Позитивный тест
def test_add_student_positive(browser, login):
    #go_to_add_student_page(browser)
    fill_and_submit_form(browser, "Иванов Иван", "20", "М", "2023-09-01", True)
    # Ждём появления сообщения об успехе
    try:
        success_alert = WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
        )
        assert "Пользователь успешно добавлен!" in success_alert.text
    except Exception:
        assert False, "Ожидалось сообщение об успешном добавлении пользователя, но оно не появилось."


# ❌ Негативный: отсутствие имени
def test_add_student_missing_name(browser, login):
    #go_to_add_student_page(browser)
    fill_and_submit_form(browser, "", "19", "Ж", "2022-01-01", False)
    # Ждём появления сообщения об успехе

    assert is_error_visible(browser, By.ID, "nameError"), "Ошибка по имени не отображается"


# ❌ Негативный: некорректный возраст
def test_add_student_invalid_age_string(browser, login):
    #go_to_add_student_page(browser)
    fill_and_submit_form(browser, "Пётр", "abc", "М", "2021-05-05", True)
    assert is_error_visible(browser, By.ID, "ageError"), "Ошибка по возрасту не отображается"

def test_add_student_invalid_age_negative(browser, login):
    fill_and_submit_form(browser, "Пётр", "-19", "М", "2021-05-05", True)
    assert is_error_visible(browser, By.ID, "ageError"), "Ошибка по возрасту не отображается"
