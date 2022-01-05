import json
import sys
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

def main():
	os.environ['WDM_LOG_LEVEL'] = '0'
	url = 'https://anilist.co/user/Piede/social'
	delay = 5

	chrome_options = Options()
	chrome_options.add_argument('disable-blink-features=AutomationControlled')
	chrome_options.add_argument('user-agent=Chrome')
	chrome_options.add_argument('--headless')



	browser = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=chrome_options)
	browser.get(url)

	html = None
	val = []
	users = []
	try:
		WebDriverWait(browser, delay).until(
			EC.presence_of_element_located((By.CSS_SELECTOR, ".name"))
		)
		time.sleep(2)
		val = browser.find_elements_by_class_name("name")
		print("got val")
		for item in val:
			print(item)
			users.append(item.text)
	except TimeoutException:
		print('Loading took too much time!')
		html = browser.page_source
	finally:
		browser.quit()


	return users


if __name__ == '__main__':
    sys.stdout.write(str(main()))