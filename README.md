# AnilistScraper

Born to visualise how many episodes my friends and I have seen in time.

Worked by scraping the anilist website to

1. Get the names of the users I follow
2. Get the episodes seen by each users, by accessing their stats page

This involved using selenium to and *scraping* that data from those pages. However, as that content is loaded asynchronously, it was a bit trickier:

```python
WebDriverWait(browser, delay).until(
	EC.presence_of_element_located((By.CSS_SELECTOR, ".value"))
)
```

-

This script *needed* therefore Chrome.
<br>In addition to that, by following many users, not all of them are loaded when scraping the content.

So I switched to the GraphQL API.

## GraphQL

Two queries, like before. One to get the users I follow, the other to retrieve the episodes they have watched:

1. Get following:

	```graphql
	query($page: Int, $perPage: Int) {
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
	```

1. Get number of eps:

	```graphql
	query($name:String) {
	    User(name: $name) {
	        statistics {
		        anime {
		            episodesWatched
		        }
	        }
	    }
	}
	```

## Generate graph

This script runs daily. As I'm ultimately interested in having a visual representation, but just of some data, I wanted to do this automatically, as well. Creating the png is handled by [graphCreator.py](graphCreator.py):
![](-epVisti.png)


## CSV or InfluxDB

This script uses the same csv structure I used for other projects. However, as there are significantly less values it didn't have the problems the others did.

Though it was unnecessary I decided to add the data to Influx anyway, to have a backup and to have some more flexible visualizations, if needed.


## Launchd

As already mentioned everything should run daily automatically. To do this I set up a service in LaunchAgents:

```
<key>ProgramArguments</key>
<array>
	<string>(path-to-project)/script.sh</string>
</array>
<key>RunAtLoad</key>
<false/>
<key>StartCalendarInterval</key>
<array>
	<dict>
		<key>Hour</key>
		<integer>18</integer>
		<key>Minute</key>
		<integer>0</integer>
	</dict>
</array>

```

This agent runs [script.sh](script.sh) at 6pm every day. The script just runs the two python scripts showed above; if they fail it shows a notification.