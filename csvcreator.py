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

def get_ep_seen(name, max_retries):
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
        response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables}, timeout=30).json()
    except requests.exceptions.RequestException:
        print("Couldn't retrieve stats of " + name)
        return get_ep_seen(name, max_retries-1)
    if("errors" in response and response["errors"][0]["status"] == 429):
        print("Rate limit exceeded, waiting 1 minute")
        time.sleep(60) # https://anilist.gitbook.io/anilist-apiv2-docs/overview/rate-limiting -> 90 requests per minute
        print("Resuming...")
        return get_ep_seen(name, max_retries)

    if(response["data"] is not None and response["data"]["User"] is not None):
        return response["data"]["User"]["statistics"]["anime"]["episodesWatched"]
    else:
        print("Couldn't retrieve stats of " + name)
        print(response)
        return get_ep_seen(name, max_retries-1)

def get_following_requests(user_id, page):
    # Here we define our query as a multi-line string
    query = '''
    query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            pageInfo {
                total
            }
            following(userId:''' + str(user_id) + ''') {
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
    response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables}, timeout=30).json()

    if("errors" in response and response["errors"][0]["status"] == 429):
        print("Rate limit exceeded, waiting 1 minute")
        time.sleep(60) # https://anilist.gitbook.io/anilist-apiv2-docs/overview/rate-limiting -> 90 requests per minute
        print("Resuming...")
        return get_following_requests(user_id, page)
    return response

def convert_to_list(json_arr):
    result = []
    for i in json_arr:
        result.append(i["name"])
    return result

def get_following(user_id):
    response = get_following_requests(user_id, 1) # First request
    total = response['data']['Page']['pageInfo']['total']
    followers = response['data']['Page']['following']
    for i in range(2, int(total/50)+2): # If the first page was not enough to contain all the users, request the next pages
        response = get_following_requests(user_id, i)
        followers = followers + response['data']['Page']['following'] # appending users
    return convert_to_list(followers)

def try_resolve_sus_users(dataframe, sus_users):
    for sus_user in sus_users:
        # find all columns where the user has a value different from -1
        columns = []
        for column in dataframe.columns:
            if dataframe.loc[dataframe['name'] == sus_user, column].values[0] != -1:
                columns.append(column)
        
        print(columns)
        print("Last column with value for user " + sus_user + ": " + columns.sort()[-1])

        
if __name__ == '__main__':
    today = datetime.today().strftime('%Y%m%d')
    users = IMPORTANT_USERS + get_following(179627) #user id of Piede
    print(users)

    # creating dataframe
    #	if not already present, creating an empty one
    if os.path.isfile(csvFilePath):
        df = pd.read_csv(csvFilePath)
    else:
        data = {'name':users}
        df = pd.DataFrame(data)

    print("Following users were found in the CSV but are not in the list of users:")
    susUsers = set(df['name']) - set(users)

    try_resolve_sus_users(df, susUsers)

    exit(0)

    # creating new column for today's date
    if(df.columns[-1] != today):
        df[today] = -1

    for user in users:
        epCount = get_ep_seen(user, 3)
        print(user + ": " + str(epCount))
        # if user is not present in the df yet
        if (len(df[df['name'] == user]) == 0):
            # we're adding him
            df.loc[len(df)] = [user]+[-1]*(len(df.columns)-1)
        
        # adding today's value in the respective cell
        if(epCount != -1):
            df.loc[df['name'] == user,today] = epCount


    df.to_csv(csvFilePath, index=False)

    script = 'display notification "Finished running ANILIST script" with title "Added all data to csv!"'
    p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    stdout, stderr = p.communicate(script)

