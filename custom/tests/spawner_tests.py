import time
import uuid
from unittest import TestCase

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys

MAX_WAIT = 2


def wait(fn):
    def modified_fn(*args, **kwargs):
        start_time = time.time()
        while True:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if time.time() - start_time > MAX_WAIT:
                    raise e
                time.sleep(0.5)

    return modified_fn


class TestClass(TestCase):
    def setUp(self):
        self.browser = webdriver.Firefox()

    def tearDown(self):
        self.browser.quit()

    @wait
    def wait_for(self, fn):
        return fn()

    def login(self):
        # username = uuid.uuid4().hex[:8]
        username = "randomuser"
        self.browser.get("http://localhost:8000/hub/home")
        # time.sleep(0.01)
        inputbox_username = self.wait_for(
            lambda: self.browser.find_element_by_id("username_input")
        )
        inputbox_username.send_keys(username)
        inputbox_password = self.wait_for(
            lambda: self.browser.find_element_by_id("password_input")
        )
        inputbox_password.send_keys(username)
        inputbox_password = self.wait_for(
            lambda: self.browser.find_element_by_id("password_input")
        )
        inputbox_password.submit()
        self.wait_for(lambda: self.browser.find_element_by_id("logout"))
        return username

    def start_default_server(self):
        start_button = self.wait_for(lambda: self.browser.find_element_by_id("start"))
        assert start_button.text == "Start My Server"
        start_button.click()
        self.wait_for(lambda: self.browser.find_element_by_id("progress-bar"))

    def get_token(self):
        self.browser.get("http://localhost:8000/hub/token")
        token_result_pre = self.wait_for(
            lambda: self.browser.find_element_by_id("token-result")
        ).text
        token_button = self.wait_for(
            lambda: self.browser.find_element_by_id("request-token-form")
        )
        token_button.submit()
        t_start = time.time()
        while True:
            token_result_post = self.wait_for(
                lambda: self.browser.find_element_by_id("token-result")
            ).text
            if token_result_post != token_result_pre:
                break
            else:
                if time.time() - t_start > 5:
                    raise Exception(
                        "No new token received - {} vs {}".format(
                            token_result_pre, token_result_post
                        )
                    )
                time.sleep(0.5)
        return token_result_post

    def cancel_with_click(self):
        cancel_button = self.wait_for(lambda: self.browser.find_element_by_id("cancel"))
        cancel_button.click()
        progress_bar_in_danger = self.wait_for(
            lambda: self.browser.find_element_by_class_name("progress-bar-danger")
        )
        """ 
        t_start = time.time()
        while True:
            progress_bar_in_danger = self.wait_for(lambda: self.browser.find_element_by_class_name("progress-bar-danger"))
            if "a":
                pass
            else:
                if time.time() - t_start > 5:
                    raise Exception("ProgressBar not jumped to 100% - {}".format(progress_bar_progress))
                time.sleep(0.5) """

    def test_vscode_is_working(self):
        a = "a"
        assert a in "abc"

    def test_site_title(self):
        self.browser.get("http://localhost:8000")
        self.assertEqual(self.browser.title, "JupyterHub")

    def test_site_login(self):
        self.login()
        start_button = self.wait_for(lambda: self.browser.find_element_by_id("start"))
        self.assertEqual(start_button.text, "Start My Server")

    def test_get_token_via_api(self):
        self.login()
        token = self.get_token()
        self.assertNotEqual(token, "")

    def test_start_server_and_cancel(self):
        self.login()
        self.start_default_server()
        self.assertIn(
            "http://localhost:8000/hub/spawn-pending/randomuser",
            self.browser.current_url,
        )
        self.cancel_with_click()
        self.browser.get("http://localhost:8000/hub/home")
        t_start = time.time()
        while True:
            start_button = self.wait_for(
                lambda: self.browser.find_element_by_id("start")
            )
            if start_button.text == "Start My Server":
                break
            else:
                if time.time() - t_start > 5:
                    raise Exception(
                        "Start Button Text still wrong: {}".format(start_button.text)
                    )
                time.sleep(0.5)
                self.browser.refresh()
        self.assertEqual(start_button.text, "Start My Server")
