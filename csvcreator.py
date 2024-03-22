"""make requests to anilist API & populate CSV"""

import os
from datetime import datetime
from subprocess import Popen, PIPE
import time

import requests
import pandas as pd

IMPORTANT_USERS = ["Piede", "OneGles", "Suzuju"]

with open('/Users/alex/AppsMine/AnilistScraper/config', encoding='utf-8') as f:
    words = f.read().split(" ")
    projectPath = words[3]
    csvFilePath = projectPath + 'historyStats.csv'

ANILIST_API_URL = 'https://graphql.anilist.co'

def getEpSeen(name, max_retries):
    """Make call request to Anilist API to get the number of episodes seen by a given user"""
    if max_retries == 0:
        return -1
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
    try:
        response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables}, timeout=200).json()
    except requests.exceptions.RequestException:
        print("Couldn't retrieve stats of " + name)
        return getEpSeen(name, max_retries-1)
    if("errors" in response and response["errors"][0]["status"] == 429):
        print("Rate limit exceeded, waiting 1 minute")
        time.sleep(60) # https://anilist.gitbook.io/anilist-apiv2-docs/overview/rate-limiting -> 90 requests per minute
        print("Resuming...")
        return getEpSeen(name, max_retries)

    if(response["data"] != None and response["data"]["User"] != None):
        return response["data"]["User"]["statistics"]["anime"]["episodesWatched"]
    else:
        print("Couldn't retrieve stats of " + name)
        print(response)
        return getEpSeen(name, max_retries-1)

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
    response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables}).json()

    if("errors" in response and response["errors"][0]["status"] == 429):
        print("Rate limit exceeded, waiting 1 minute")
        time.sleep(60) # https://anilist.gitbook.io/anilist-apiv2-docs/overview/rate-limiting -> 90 requests per minute
        print("Resuming...")
        return getFollowingRequest(id, page)
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
users = IMPORTANT_USERS + getFollowing(179627) #user id of Piede
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
    epCount = getEpSeen(user, 3)
    print(user + ": " + str(epCount))
    # if user is not present in the df yet
    if (len(df[df['name'] == user]) == 0):
        # we're adding him
        df.loc[len(df)] = [user]+[-1]*(len(df.columns)-1)
    
    # adding today's value in the respective cell
    if(epCount != -1):
        df.loc[df['name'] == user,today] = epCount


df.to_csv(csvFilePath, index=False)


# todo change to sqlite	
# with InfluxDBClient(url="http://localhost:8086", token=token, org=org) as client:
# 	write_api = client.write_api(write_options=SYNCHRONOUS)

# 	dateObj = datetime.utcnow()

# 	for index, row in df.iterrows():
# 		name = row['name']
# 		count = df[today][index]
        
# 		# Ignoring -1 values (missing records)
# 		if(count != -1):
# 			print(str(dateObj) + " - " + name + ": " + str(count))
# 			point = Point(name) \
# 				.field("viewed_episodes", count) \
# 				.time(dateObj, WritePrecision.NS)
# 			try:
# 				write_api.write(bucket, org, point)
# 			except:
# 				client.close()
# 				script = 'display notification "Error in ANILIST script" with title "Cannot connect to influx!"'
# 				p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
# 				stdout, stderr = p.communicate(script)
# 				exit(0)



script = 'display notification "Finished running ANILIST script" with title "Added all data to csv!"'
p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
stdout, stderr = p.communicate(script)
# client.close()