from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from cbng_reviewer.models import Edit, User, Classification, EditGroup


class ReviewInterfaceTestCase(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.add_argument("--headless")
        cls.driver = webdriver.Chrome(options)

    @classmethod
    def tearDownClass(cls):
        cls.driver.close()
        cls.driver.quit()
        super().tearDownClass()

    def _authenticate_as_reviewer(self):
        self.client.force_login(User.objects.create(username="test-user", is_reviewer=True))
        session_cookie = self.client.cookies["sessionid"]

        self.driver.get(self.live_server_url)  # Must be on domain we are setting the cookie for
        self.driver.add_cookie({"name": session_cookie.key, "value": session_cookie.value, "path": "/"})

    def testNoEditsPending(self):
        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")
        WebDriverWait(self.driver, 5).until(EC.alert_is_present())
        alert = Alert(self.driver)
        self.assertEqual(alert.text, "No Pending Edit Found")
        alert.accept()

    def testEditLoad(self):
        edit_group = EditGroup.objects.create(name="Example Group", weight=20)
        edit = Edit.objects.create(id=688772969, classification=1)
        edit.groups.add(edit_group)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))

        # Basic checks
        edit_id = self.driver.find_element(by=By.ID, value="edit_id").text
        self.assertEqual(edit_id, f"{edit.id}")

        iframe = self.driver.find_element(by=By.ID, value="iframe")
        self.assertEqual(
            iframe.get_attribute("src"), "https://en.wikipedia.org/w/index.php?action=view&diffonly=1&diff=688772969"
        )

    def testNormalRenderMode(self):
        edit_group = EditGroup.objects.create(name="Example Group", weight=20)
        edit = Edit.objects.create(id=688772969, classification=1)
        edit.groups.add(edit_group)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))

        # Switch to normal
        input = self.driver.find_element(by=By.XPATH, value="//input[@type='radio'][@name='url_type'][@value='n']")
        input.click()

        # Wait for loading
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))

        # Should have the new url loaded
        iframe = self.driver.find_element(by=By.ID, value="iframe")
        self.assertEqual(iframe.get_attribute("src"), "https://en.wikipedia.org/w/index.php?action=view&diff=688772969")

    def testDiffRenderMode(self):
        edit_group = EditGroup.objects.create(name="Example Group", weight=20)
        edit = Edit.objects.create(id=688772969, classification=1)
        edit.groups.add(edit_group)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))

        # Switch to normal
        input = self.driver.find_element(by=By.XPATH, value="//input[@type='radio'][@name='url_type'][@value='d']")
        input.click()

        # Wait for loading
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))

        # Should have the new url loaded
        iframe = self.driver.find_element(by=By.ID, value="iframe")
        self.assertEqual(
            iframe.get_attribute("src"), "https://en.wikipedia.org/w/index.php?action=view&diffonly=1&diff=688772969"
        )

    def testRenderOnlyMode(self):
        edit_group = EditGroup.objects.create(name="Example Group", weight=20)
        edit = Edit.objects.create(id=688772969, classification=1)
        edit.groups.add(edit_group)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))

        # Switch to normal
        input = self.driver.find_element(by=By.XPATH, value="//input[@type='radio'][@name='url_type'][@value='r']")
        input.click()

        # Wait for loading
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))

        # Should have the new url loaded
        iframe = self.driver.find_element(by=By.ID, value="iframe")
        self.assertEqual(
            iframe.get_attribute("src"), "https://en.wikipedia.org/w/index.php?action=render&diffonly=1&diff=688772969"
        )

    def testClassifyAsVandalismUsingButton(self):
        # Weight so we know this will be the first one
        edit_group_1 = EditGroup.objects.create(name="Example Group 1", weight=20)
        edit_1 = Edit.objects.create(id=688772969)
        edit_1.groups.add(edit_group_1)

        # Provide a second one so the flow is 'normal' i.e. no alert
        edit_group_2 = EditGroup.objects.create(name="Example Group 2", weight=10)
        edit_2 = Edit.objects.create(id=695551216)
        edit_2.groups.add(edit_group_2)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_1.id}")

        # Classify
        button = self.driver.find_element(by=By.XPATH, value="//span[@id='classify']//button[text()='Vandalism']")
        button.click()

        # Check we loaded the next edit
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_2.id}")

        # Check we stored the value
        self.assertTrue(Classification.objects.filter(edit=edit_1, classification=0).exists())

    def testClassifyAsVandalismUsingKeyboard(self):
        # Weight so we know this will be the first one
        edit_group_1 = EditGroup.objects.create(name="Example Group 1", weight=20)
        edit_1 = Edit.objects.create(id=688772969)
        edit_1.groups.add(edit_group_1)

        # Provide a second one so the flow is 'normal' i.e. no alert
        edit_group_2 = EditGroup.objects.create(name="Example Group 2", weight=10)
        edit_2 = Edit.objects.create(id=695551216)
        edit_2.groups.add(edit_group_2)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_1.id}")

        # Classify
        actions = ActionChains(self.driver)
        actions.send_keys(Keys.ARROW_LEFT)
        actions.perform()

        # Check we loaded the next edit
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_2.id}")

        # Check we stored the value
        self.assertTrue(Classification.objects.filter(edit=edit_1, classification=0).exists())

    def testClassifyAsConstructiveUsingButton(self):
        # Weight so we know this will be the first one
        edit_group_1 = EditGroup.objects.create(name="Example Group 1", weight=20)
        edit_1 = Edit.objects.create(id=688772969)
        edit_1.groups.add(edit_group_1)

        # Provide a second one so the flow is 'normal' i.e. no alert
        edit_group_2 = EditGroup.objects.create(name="Example Group 2", weight=10)
        edit_2 = Edit.objects.create(id=695551216)
        edit_2.groups.add(edit_group_2)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_1.id}")

        # Classify
        button = self.driver.find_element(by=By.XPATH, value="//span[@id='classify']//button[text()='Constructive']")
        button.click()

        # Check we loaded the next edit
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_2.id}")

        # Check we stored the value
        self.assertTrue(Classification.objects.filter(edit=edit_1, classification=1).exists())

    def testClassifyAsConstructiveUsingKeyboard(self):
        # Weight so we know this will be the first one
        edit_group_1 = EditGroup.objects.create(name="Example Group 1", weight=20)
        edit_1 = Edit.objects.create(id=688772969)
        edit_1.groups.add(edit_group_1)

        # Provide a second one so the flow is 'normal' i.e. no alert
        edit_group_2 = EditGroup.objects.create(name="Example Group 2", weight=10)
        edit_2 = Edit.objects.create(id=695551216)
        edit_2.groups.add(edit_group_2)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_1.id}")

        # Classify
        actions = ActionChains(self.driver)
        actions.send_keys(Keys.ARROW_RIGHT)
        actions.perform()

        # Check we loaded the next edit
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_2.id}")

        # Check we stored the value
        self.assertTrue(Classification.objects.filter(edit=edit_1, classification=1).exists())

    def testClassifyAsSkipUsingButton(self):
        # Weight so we know this will be the first one
        edit_group_1 = EditGroup.objects.create(name="Example Group 1", weight=20)
        edit_1 = Edit.objects.create(id=688772969)
        edit_1.groups.add(edit_group_1)

        # Provide a second one so the flow is 'normal' i.e. no alert
        edit_group_2 = EditGroup.objects.create(name="Example Group 2", weight=10)
        edit_2 = Edit.objects.create(id=695551216)
        edit_2.groups.add(edit_group_2)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_1.id}")

        # Classify
        button = self.driver.find_element(by=By.XPATH, value="//span[@id='classify']//button[text()='Skip']")
        button.click()

        # Check we loaded the next edit
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_2.id}")

        # Check we stored the value
        self.assertTrue(Classification.objects.filter(edit=edit_1, classification=2).exists())

    def testClassifyAsSkipUsingKeyboard(self):
        # Weight so we know this will be the first one
        edit_group_1 = EditGroup.objects.create(name="Example Group 1", weight=20)
        edit_1 = Edit.objects.create(id=688772969)
        edit_1.groups.add(edit_group_1)

        # Provide a second one so the flow is 'normal' i.e. no alert
        edit_group_2 = EditGroup.objects.create(name="Example Group 2", weight=10)
        edit_2 = Edit.objects.create(id=695551216)
        edit_2.groups.add(edit_group_2)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_1.id}")

        # Classify
        actions = ActionChains(self.driver)
        actions.send_keys(Keys.ARROW_UP)
        actions.perform()

        # Check we loaded the next edit
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_2.id}")

        # Check we stored the value
        self.assertTrue(Classification.objects.filter(edit=edit_1, classification=2).exists())

    def testConflictingClassificationAbort(self):
        edit_group_1 = EditGroup.objects.create(name="Example Group 1", weight=20)
        edit_1 = Edit.objects.create(id=688772969, classification=1)
        edit_1.groups.add(edit_group_1)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_1.id}")

        # Classify
        button = self.driver.find_element(by=By.XPATH, value="//span[@id='classify']//button[text()='Vandalism']")
        button.click()

        WebDriverWait(self.driver, 5).until(EC.alert_is_present())
        alert = Alert(self.driver)
        self.assertEqual(alert.text, "Are you sure?")
        alert.dismiss()

        # Check we are on the same edit
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_1.id}")

        # Check we have no classification
        self.assertFalse(Classification.objects.filter(edit=edit_1, classification=0).exists())

    def testConflictingClassificationConfirm(self):
        # Weight so we know this will be the first one
        edit_group_1 = EditGroup.objects.create(name="Example Group 1", weight=20)
        edit_1 = Edit.objects.create(id=688772969, classification=1)
        edit_1.groups.add(edit_group_1)

        # Provide a second one so the flow is 'normal' i.e. no alert
        edit_group_2 = EditGroup.objects.create(name="Example Group 2", weight=10)
        edit_2 = Edit.objects.create(id=695551216)
        edit_2.groups.add(edit_group_2)

        self._authenticate_as_reviewer()
        self.driver.get(f"{self.live_server_url}/review")

        # Wait for loading
        loading_spinner = self.driver.find_element(by=By.ID, value="spinner")
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_1.id}")

        # Classify
        button = self.driver.find_element(by=By.XPATH, value="//span[@id='classify']//button[text()='Vandalism']")
        button.click()

        WebDriverWait(self.driver, 5).until(EC.alert_is_present())
        alert = Alert(self.driver)
        self.assertEqual(alert.text, "Are you sure?")
        alert.accept()

        # Check we loaded the next edit
        WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(loading_spinner))
        self.assertEqual(self.driver.find_element(by=By.ID, value="edit_id").text, f"{edit_2.id}")

        # Check we stored the value
        self.assertTrue(Classification.objects.filter(edit=edit_1, classification=0).exists())
