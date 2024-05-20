"""make requests to anilist API & populate CSV"""

import os
from datetime import datetime
from subprocess import Popen, PIPE
import time

import requests
import pandas as pd
import numpy as np

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

    if("data" in response and response["data"] is not None and response["data"]["User"] is not None):
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

def is_user_present(value):
    res = not ((isinstance(value, np.float64) or isinstance(value, float)) and np.isnan(value)) and (value != 0.0)
    # print(str(res) + " " + str(type(value)) + " " + str(value) + " " + str(isinstance(value, np.float64)) + " " + str(isinstance(value, float)) + " " + str(np.isnan(value)) + " " + str(value != 0.0))
    return res

def parse_date(date_str):
    return datetime.strptime(date_str, '%Y%m%d')

def try_resolve_sus_users(dataframe, sus_users, following_users):
    print("Finding first appearence for all following users...")
    # for all following_users, check what is the first column where the user is present
    following_users_first_appearence = {}
    for user in following_users + list(sus_users):
        columns = []
        for column in dataframe.columns:
            cell_value = dataframe.loc[dataframe['name'] == user, column].values[0]
            if column == 'name':
                continue
            if is_user_present(cell_value):
                columns.append({"column": column, "value": cell_value})
        columns.sort(key=lambda x: x["column"])
        if len(columns) == 0:
            print("ERROR: User " + user + " has no values")
            continue
        following_users_first_appearence[user] = columns[0]
    print("First appearence for all following users found" + str(following_users_first_appearence))

    for sus_user in sus_users:
        print("\nResolving sus user " + sus_user)
        columns = []
        for column in dataframe.columns: # find last column with value != -1 (user still existed at that time)
            cell_value = dataframe.loc[dataframe['name'] == sus_user, column].values[0]
            if column == 'name':
                continue
            if is_user_present(cell_value):
                columns.append({"column": column, "value": cell_value})
        columns.sort(key=lambda x: x["column"])
        if len(columns) == 0:
            print("ERROR: User " + sus_user + " has no values")
            continue
        last_appearence = columns[-1]
        # check if there is a user that has first appearence on that day or after and has same or greater value 
        # if so, we can assume that the user is the same
        possible_users = []
        for user, first_appearence in following_users_first_appearence.items():
            if user == sus_user:
                continue
            if parse_date(first_appearence["column"]) >= parse_date(last_appearence["column"]):
                if first_appearence["value"] >= last_appearence["value"]:
                    possible_users.append({"user": user, "first_appearence": first_appearence})

        possible_users.sort(key=lambda x: x["first_appearence"]["column"])
        print("lastAppearence: " + str(last_appearence))
        for user in possible_users:
            # print spaces to make sure the stuff after is aligned
            # get index of column last_appearence["column"] in dataframe columns
            index_last = dataframe.columns.get_loc(last_appearence["column"])
            index_first = dataframe.columns.get_loc(user["first_appearence"]["column"])

            columns_between = index_first - index_last
            print("\t" + user["user"].ljust(20) + " - since " + user["first_appearence"]["column"] + "(" + str(columns_between) + ") with " + str(user["first_appearence"]["value"]))
            if columns_between <= 1:
                # most probably the same user, skipping the rest
                break

def merge_sus_users(dataframe, sus_users_mapping):
    for sus_user, user in sus_users_mapping.items():
        for column in dataframe.columns:
            if len(dataframe.loc[dataframe['name'] == sus_user, column].values) == 0: # todo not working
                continue
            sus_value = dataframe.loc[dataframe['name'] == sus_user, column].values[0]
            if len(dataframe.loc[dataframe['name'] == user, column].values) == 0:
                if is_user_present(sus_value):
                    dataframe.loc[dataframe['name'] == user, column] = sus_value
            else:
                user_value = dataframe.loc[dataframe['name'] == user, column].values[0]
                if is_user_present(sus_value) and not is_user_present(user_value):
                    dataframe.loc[dataframe['name'] == user, column] = sus_value
                elif is_user_present(sus_value) and is_user_present(user_value):
                    if sus_value > user_value:
                        dataframe.loc[dataframe['name'] == user, column] = sus_value

        dataframe = dataframe[dataframe['name'] != sus_user]
        print("Merged " + sus_user + " into " + user)
    return dataframe

        
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
    # todo add option to run in background which ignores all this stuff
    # print("Following users were found in the CSV but are not in the list of users:")
    # susUsers = set(df['name']) - set(users)
    # print(susUsers)
    # if len(susUsers) > 0:
    #     try_resolve_sus_users(df, susUsers, users)

    # sus_users_mapping = {
    #     "CrowAmasawa": "LordGwyn",
    #     "CaptainTree": "Tree",
    #     "DonJuwuan": "Tensarte",
    #     "DatenshiCrow": "CrowSkirata",
    #     "CrowSkirata": "CrowAmasawa",
    #     "LiyuuSix": "Flacc",
    #     "aviralgupta393": "Hachiken"
    # }
    # if len(sus_users_mapping) > 0:
    #     df = merge_sus_users(df, sus_users_mapping)
    #     df = df.replace(-1, np.nan) # remove values that are -1, should be saved as ,, in csv
    #     df.to_csv(csvFilePath, index=False, float_format='%.0f')
    #     exit(0)

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

    df = df.replace(-1, np.nan) # remove values that are -1, should be saved as ,, in csv
    df.to_csv(csvFilePath, index=False, float_format='%.0f')

    script = 'display notification "Finished running ANILIST script" with title "Added all data to csv!"'
    p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    stdout, stderr = p.communicate(script)

