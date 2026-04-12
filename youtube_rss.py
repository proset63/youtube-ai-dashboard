import feedparser

def get_videos(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(url)

    videos = []

    for entry in feed.entries:
        videos.append({
            "channel_id": channel_id,
            "title": entry.title,
            "link": entry.link,
            "summary": entry.summary
        })

    return videos