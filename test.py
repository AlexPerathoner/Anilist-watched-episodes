import requests

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
    print(response)
    return response["data"]["User"]["statistics"]["anime"]["episodesWatched"]
    
print(getEpSeen("Piede"))