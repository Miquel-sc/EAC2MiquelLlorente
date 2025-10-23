from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from django.contrib.auth.models import User, Permission
from polls.models import Question


class MySeleniumTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        opts = Options()
        opts.add_argument("--headless")  # Mode headless per CI/CD
        cls.selenium = webdriver.Firefox(options=opts)
        cls.selenium.implicitly_wait(5)

        # Creo l'usuari admin que és isard
        user = User.objects.create_user("isard", "isard@isardvdi.com", "pirineus")
        user.is_superuser = True
        user.is_staff = True
        user.save()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    # -----------------------------
    # Funcions auxiliars per entrar amb l'usuari i sortir 
    # -----------------------------
    def login(self, username, password):
        """Inicia sessió a /admin/"""
        self.selenium.get(f"{self.live_server_url}/admin/login/")
        self.selenium.find_element(By.NAME, "username").send_keys(username)
        self.selenium.find_element(By.NAME, "password").send_keys(password)
        self.selenium.find_element(By.XPATH, "//input[@value='Log in']").click()

    def logout(self):
        """Fa logout clicant el botó del formulari de logout"""
        logout_button = WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//form[@id='logout-form']//button[text()='Log out']")
            )
        )
        logout_button.click()

    # -----------------------------
    # TEST PRINCIPAL
    # -----------------------------
    def test_user_can_create_questions_but_not_users(self):
        # Login com a superusuari
        self.login("isard", "pirineus")

        # Crear usuari staff
        self.selenium.get(f"{self.live_server_url}/admin/auth/user/add/")
        self.selenium.find_element(By.NAME, "username").send_keys("staff")
        self.selenium.find_element(By.NAME, "password1").send_keys("pirineus")
        self.selenium.find_element(By.NAME, "password2").send_keys("pirineus")
        self.selenium.find_element(By.NAME, "_save").click()

        # Assignar-lo com a staff i donar-li permisos per Question
        staff_user = User.objects.get(username="staff")
        staff_user.is_staff = True
        perms = Permission.objects.filter(
            codename__in=["add_question", "view_question"]
        )
        staff_user.user_permissions.set(perms)
        staff_user.save()

        # Logout com a superusuari
        self.logout()

        # Login com a staff
        self.login("staff", "pirineus")

        # Comprovar que pot veure el model "Questions"
        self.selenium.get(f"{self.live_server_url}/admin/")
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Questions"))
        )

        # Crear una nova Question amb WebDriverWait
        self.selenium.find_element(By.LINK_TEXT, "Questions").click()

        add_question_link = WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//tr[contains(@class, 'model-question')]//a[contains(@href, '/add/')]")
            )
        )
        add_question_link.click()

        # Omplir el formulari de Question
        self.selenium.find_element(By.NAME, "question_text").send_keys("Hola funciona bé?")
        self.selenium.find_element(By.NAME, "pub_date_0").send_keys("2025-01-01")
        self.selenium.find_element(By.NAME, "pub_date_1").send_keys("12:00:00")
        self.selenium.find_element(By.NAME, "_save").click()

        # Comprovar que s'ha creat correctament
        self.assertTrue(
            Question.objects.filter(question_text="Hola funciona bé?").exists()
        )

        # Comprovar que NO pot veure ni crear usuaris
        try:
            self.selenium.find_element(By.LINK_TEXT, "Users")
            assert False, "ERROR: L'usuari limitat pot veure Users!"
        except NoSuchElementException:
            pass  # Correcte: no pot veure Users

        # Logout final
        self.logout()
