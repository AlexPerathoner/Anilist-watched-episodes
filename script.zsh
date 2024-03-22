
/usr/local/bin/python3.11 "/Users/alex/AppsMine/AnilistScraper/csvcreator.py" || /usr/bin/osascript -e 'display notification "Could not run ANILIST script"';
/usr/local/bin/python3.11 "/Users/alex/AppsMine/AnilistScraper/graphCreator.py" || /usr/bin/osascript -e 'display notification "Could not run ANILIST script (graph creator)"';

