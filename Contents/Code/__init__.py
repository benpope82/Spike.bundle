RE_TITLE = Regex('(.+?) \([0-9]+\)')
RE_SEASON = Regex('Season ([0-9]+)')

BASE_URL = "http://www.spike.com"
MRSS_PATH = "http://www.comedycentral.com/feeds/mrss?uri=%s"
MRSS_NS = {"media": "http://search.yahoo.com/mrss/"}
####################################################################################################
def Start():

    ObjectContainer.title1 = "Spike"
    #HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:13.0) Gecko/20100101 Firefox/13.0.1'

####################################################################################################
@handler("/video/spike", "Spike")
def MainMenu():

    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(EpsOrClipsShow, url=BASE_URL + '/episodes', title="Full Episodes", show_type='full'), title="Full Episodes"))
    oc.add(DirectoryObject(key=Callback(EpsOrClipsShow, url=BASE_URL + '/video-clips', title="Video Clips", show_type='clip'), title="Video Clips"))
    return oc

####################################################################################################
@route("/video/spike/epsorclipsshow")
def EpsOrClipsShow(title, url, show_type):

    oc = ObjectContainer(title2=title)
    data = HTML.ElementFromURL(url)

    for show in data.xpath('//div[@class="middle"]/ul/li/a'):
        show_title = show.text
        show_link = show.get('href')
        if '/events/' in show_link or '/shows/e3' in show_link or not show_title:
            continue
        else:
            if show_type == 'full' and 'video-clips' not in show_link:
                show_link = show_link.split('episodes/')[1]
                show_link = BASE_URL + '/episodes/' + show_link.split('/')[0]
                oc.add(DirectoryObject(key=Callback(ShowBrowser, show_url=show_link, show_title=show_title), title=show_title))
            else:
                oc.add(DirectoryObject(key=Callback(ClipBrowser, show_url=show_link, show_title=show_title), title=show_title))

    oc.objects.sort(key = lambda obj: obj.title)

    if len(oc) < 1:
        return ObjectContainer(header="Empty", message="No content found.")

    return oc
####################################################################################################
@route("/video/spike/showbrowser")
def ShowBrowser(show_url, show_title):

    oc = ObjectContainer(title2=show_title)

    if not show_url.startswith('http://'):
        show_url = BASE_URL + show_url

    data = HTML.ElementFromURL(show_url)

    for season in data.xpath('//ul[@class="season_navigation"]//a'):
        season_title = season.text
        season_url = season.get('href')
        oc.add(DirectoryObject(key=Callback(EpisodeBrowser, show_title=show_title, season_url=season_url, season_title=season_title), title=season_title))

    if len(oc) == 1:
        return EpisodeBrowser(show_title=show_title, season_url=season_url)

    return oc

####################################################################################################
@route("/video/spike/episodebrowser")
def EpisodeBrowser(show_title, season_url, season_title=None):

    oc = ObjectContainer(title1=show_title, title2=season_title)

    try:
        season_index = RE_SEASON.search(season_title).group(1)
    except:
        season_index = None

    data = HTML.ElementFromURL(season_url)

    for ep in data.xpath('//div[contains(@class, "episode_guide")]'):
        try:
            ep_url = ep.xpath('.//a[@class="title"]')[0].get('href')
        except:
            continue
        episode_type = ep.xpath('.//div[@class="full"]//span[@class="title"]')[0].text
        Log(episode_type)
        if episode_type == "episode highlights":
            #highlight reels don't work with the URL Service for some reason and who wants to watch
            #episode highlights anyway. Exclude that sh!t from the episode list.
            continue

        ep_title = ep.xpath('.//img')[0].get('title')
        ep_thumb = ep.xpath('.//img')[0].get('src').split('?')[0]
        ep_summary = ep.xpath('.//div[@class="description"]//p')[0].text.strip()

        if season_index:
            ep_index = ep_url.split('-')[-1].replace(season_index, '', 1).lstrip('0').strip('s')
        else:
            ep_index = ep_url.split('-')[-1].strip('s')
        # found that one ep_index was giving an error due to being empty so added exception
        if not ep_index:
            ep_index=0
        ep_airdate = ep.xpath('.//p[@class="aired_available"]/text()')[0].strip()
        ep_date = Datetime.ParseDate(ep_airdate).date()
		
        if season_index:
            oc.add(EpisodeObject(url=ep_url, title=ep_title, show=show_title, summary=ep_summary, index=int(ep_index), season=int(season_index),
                originally_available_at=ep_date, thumb=Resource.ContentsOfURLWithFallback(url=ep_thumb)))
        else:
            oc.add(EpisodeObject(url=ep_url, title=ep_title, show=show_title, summary=ep_summary, absolute_index=int(ep_index),
                originally_available_at=ep_date, thumb=Resource.ContentsOfURLWithFallback(url=ep_thumb)))
	
    try:
        next_page = data.xpath('//div[@class="pagination"]//a')[-1]
        if next_page.text == 'Next':
            next_url = next_page.get('href')
            oc.add(NextPageObject(key=Callback(EpisodeBrowser, show_title=show_title, season_url=next_url, season_title=season_title), title="Next Page"))
    except:
        pass
	
    if len(oc) == 0:
        return ObjectContainer(header="Spike", message="There are no titles available for the requested item.")
	
    return oc

####################################################################################################
@route("/video/spike/clipbrowser")
def ClipBrowser(show_url, show_title):
    oc = ObjectContainer(title2=show_title)
	
    if show_url.startswith('http://'):
        pass
    else:
        show_url = BASE_URL + show_url

    data = HTML.ElementFromURL(show_url)
    for clip in data.xpath('//div[@id="show_clips_res"]//div[@class="block"]'):
        clip_url 	= clip.xpath('.//a')[0].get('href')
        clip_thumb 	= clip.xpath('.//img')[0].get('src').split('?')[0]
        clip_title 	= clip.xpath('.//h3/a')[0].text
        clip_runtime	= clip.xpath('.//h3/small')[0].text.strip('(').strip(')')
        clip_duration	= Datetime.MillisecondsFromString(clip_runtime)
        try:
            posted_date = clip.xpath('.//div[@class="af_content"]/small')[0].text.strip('Posted ')
            clip_date = Datetime.ParseDate(posted_date).date()
        except:
            clip_date = None
        clip_summary = clip.xpath('.//div[@class="af_content"]/p')[0].text

        oc.add(VideoClipObject(url=clip_url, title=clip_title, summary=clip_summary, duration=clip_duration, originally_available_at=clip_date,
            thumb=Resource.ContentsOfURLWithFallback(url=clip_thumb)))

    try:
        # the paging for the feeds for the videos do not always have the full and proper url in the paging, so this works instead
        if '/feeds/' in show_url:
            feed_page = show_url.split('?')[0]
        else:
            feed_page = data.xpath('//div[@class="v_content"]//@data-url')[0]
        all_pages = data.xpath('//div[@class="pagination"]/div/ul/li/a//text()')
        next_page = int(data.xpath('//div[@class="pagination"]/div/ul/li/span//text()')[0]) + 1
        next_page = str(next_page)
        if next_page in all_pages:
            next_url = feed_page + '?page=' + next_page
            oc.add(NextPageObject(key=Callback(ClipBrowser, show_url=next_url, show_title=show_title), title="Next Page"))
    except:
        pass

    return oc
