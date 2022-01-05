import os
from datetime import datetime

import requests
import sys
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from subprocess import Popen, PIPE

token = "m3_qTJNHan6NP0jFkdkLjFUdtNy5cCnFnQpWQVfDDUXQtmMf8o-udOP8t9yxPDKQHkvKqPtvJpKLdO-FaoG4mQ=="
org = "AlexPera"
bucket = "AnilistStats"

chrome_options = Options()
chrome_options.add_argument('disable-blink-features=AutomationControlled')
chrome_options.add_argument('user-agent=Chrome')
chrome_options.add_argument('--headless')

browser = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=chrome_options)


def getEpSeen(name):

	os.environ['WDM_LOG_LEVEL'] = '0'
	if(name == ""):
		name = sys.argv[1]
	url = 'https://anilist.co/user/'+name+'/stats/anime/overview'
	delay = 5

	browser.get(url)

	val = []
	count = -1
	try:
		WebDriverWait(browser, delay).until(
			EC.presence_of_element_located((By.CSS_SELECTOR, ".value"))
		)
		val = browser.find_elements_by_class_name("value") 
		print(name + ": " + val[1].text)
		count = val[1].text

	except TimeoutException:
		print("Failed to load ep seen by " + name)

	return count


def request(id, page):
# Here we define our query as a multi-line string
    query = '''
    query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
        pageInfo {
            total
            perPage
        }
        following(userId:''' + str(id) + ''') {
        name
        }
    }
    }
    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'page': page
    }

    url = 'https://graphql.anilist.co'
    # Make the HTTP Api request
    response = requests.post(url, json={'query': query, 'variables': variables}).json()
    return response

def convertToList(jsonArr):
    result = []
    for i in jsonArr:
        result.append(i["name"])

    return result

def getFollowers(id):
    response = request(id, 1)
    total = response['data']['Page']['pageInfo']['total']
    followers = response['data']['Page']['following']

    for i in range(2, int(total/50)+2):
        response = request(id, i)
        followers = followers + response['data']['Page']['following']

    return convertToList(followers)


today = datetime.today().strftime('%Y%m%d')
users = getFollowers(179627) #user id of Piede
print(users)
if os.path.isfile('/Users/alex/AppsMine/AnilistScraper/historyStats.csv'):
	df = pd.read_csv('/Users/alex/AppsMine/AnilistScraper/historyStats.csv')
else:
	data = {'name':users}
	df = pd.DataFrame(data)

#creiamo la nuova colonna
if(df.columns[-1] != today):
	df[today] = -1
for user in users:
	epCount = getEpSeen(user)
	#check if user doesn't exists yet
	if (len(df[df['name'] == user]) == 0):
		#creating one
		df.loc[len(df)] = [user]+[-1]*(len(df.columns)-1)
	
	df.loc[df['name'] == user,today] = epCount


df.to_csv('/Users/alex/AppsMine/AnilistScraper/historyStats.csv', index=False)



with InfluxDBClient(url="http://localhost:8086", token=token, org=org) as client:
	write_api = client.write_api(write_options=SYNCHRONOUS)
	for index, row in df.iterrows():
		name = row['name']
		count = df[today][index]
		
		dateObj = datetime.strptime(today, "%Y%m%d")
		if(count != -1):

			print(str(dateObj) + " - " + name + ": " + str(count))
			point = Point(name) \
				.field("viewed_episodes", count) \
				.time(dateObj, WritePrecision.NS)
			
			#write_api.write(bucket, org, point)


browser.quit()

script = 'display notification "Finished running ANILIST script" with title "Added all data to Influx!"'
p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
stdout, stderr = p.communicate(script)