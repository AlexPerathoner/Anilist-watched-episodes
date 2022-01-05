import os
from datetime import datetime

import requests
import pandas as pd

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from subprocess import Popen, PIPE


with open('old-other/token') as f:
    token = f.read()

org = "AlexPera"
bucket = "AnilistStats"

def getEpSeen(name):
    query = '''
    query($name:String) {
    User(name: $name) {
        statistics {
        anime {
            episodesWatched
        }
        }
    }
    }
    '''
    # Define our query variables and values that will be used in the query request
    variables = {
        'name': name
    }

    url = 'https://graphql.anilist.co'
    # Make the HTTP Api request
    response = requests.post(url, json={'query': query, 'variables': variables}).json()
    return response["data"]["User"]["statistics"]["anime"]["episodesWatched"]


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
	print(user + ": " + str(epCount))
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
			
			write_api.write(bucket, org, point)



script = 'display notification "Finished running ANILIST script" with title "Added all data to Influx!"'
p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
stdout, stderr = p.communicate(script)