import os
from datetime import datetime

import requests
import pandas as pd

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from subprocess import Popen, PIPE


# get InfluxDB Token
with open('config') as f:
	words = f.read().split(" ")
	token = words[0]
	org = words[1]
	bucket = words[2]
	projectPath = words[3]
	csvFilePath = projectPath + 'historyStats.csv'

anilistApiUrl = 'https://graphql.anilist.co'

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
    # Make the HTTP Api request
    response = requests.post(anilistApiUrl, json={'query': query, 'variables': variables}).json()
    return response["data"]["User"]["statistics"]["anime"]["episodesWatched"]


def getFollowingRequest(id, page):
	# Here we define our query as a multi-line string
    query = '''
    query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
			pageInfo {
				total
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
    # Make the HTTP Api request
    response = requests.post(anilistApiUrl, json={'query': query, 'variables': variables}).json()
    return response

def convertToList(jsonArr):
    result = []
    for i in jsonArr:
        result.append(i["name"])

    return result

def getFollowing(id):
    response = getFollowingRequest(id, 1) # First request
    total = response['data']['Page']['pageInfo']['total']
    followers = response['data']['Page']['following']

    for i in range(2, int(total/50)+2): # If the first page was not enough to contain all the users, request the next pages
        response = getFollowingRequest(id, i)
        followers = followers + response['data']['Page']['following'] # appending users

    return convertToList(followers)


today = datetime.today().strftime('%Y%m%d')
users = getFollowing(179627) #user id of Piede
print(users)

 # creating dataframe
 #	if not already present, creating an empty one
if os.path.isfile(csvFilePath):
	df = pd.read_csv(csvFilePath)
else:
	data = {'name':users}
	df = pd.DataFrame(data)

# creating new column for today's date
if(df.columns[-1] != today):
	df[today] = -1

for user in users:
	epCount = getEpSeen(user)
	print(user + ": " + str(epCount))
	# if user is not present in the df yet
	if (len(df[df['name'] == user]) == 0):
		# we're adding him
		df.loc[len(df)] = [user]+[-1]*(len(df.columns)-1)
	
	# adding today's value in the respective cell
	df.loc[df['name'] == user,today] = epCount


df.to_csv(csvFilePath, index=False)


with InfluxDBClient(url="http://localhost:8086", token=token, org=org) as client:
	write_api = client.write_api(write_options=SYNCHRONOUS)
	dateObj = datetime.strptime(today, "%Y%m%d")

	for index, row in df.iterrows():
		name = row['name']
		count = df[today][index]
		
		# Ignoring -1 values (missing records)
		if(count != -1):
			print(str(dateObj) + " - " + name + ": " + str(count))
			point = Point(name) \
				.field("viewed_episodes", count) \
				.time(dateObj, WritePrecision.NS)
			
			write_api.write(bucket, org, point)



script = 'display notification "Finished running ANILIST script" with title "Added all data to Influx!"'
p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
stdout, stderr = p.communicate(script)