import urllib, requests, os
from shutil import copyfileobj
from config import config
from clients.telegram_client import telegramClient

def bytesConversor (b):
    if b > 1024 and b < 1024*1024:
        return '{:.2f} KB'.format(b/1024)
    elif b >= 1024*1024 and b < 1024*1024*1024:
        return '{:.2f} MB'.format(b/(1024*1024))
    elif b >= 1024*1024*1024 and b < 1024*1024*1024*1024:
        return '{:.2f} GB'.format(b/(1024*1024*1024))
    elif b >= 1024*1024*1024*1024:
        return '{:.2f} PB'.format(b/(1024*1024*1024*1024))
    else:
        return '{:.2f} B'.format(b)

def getFileFromURL(url, filename):
    try:
        urllib.request.urlretrieve(url, filename)
    except:
        photo_rq = requests.get(url, stream=True)
        with open(filename, 'wb') as out_file:
            copyfileobj(photo_rq.raw, out_file)
        del photo_rq

def percentToEmoji(percent):
    if percent > 0 and percent < 30:
        return '🟢'
    if percent >= 30 and percent < 60:
        return '🟡'
    if percent >= 60 and percent < 90:
        return '🟠'
    if percent >= 90:
        return '🔴'
    return '⚪'

def weatherEmoji(code):
    if code >= 200 and code <= 202:
        return '⛈️💧'
    if code >= 230 and code <= 233:
        return '🌩️⚡'
    if code >= 300 and code <= 302:
        return '🌨️❄️'
    if code >= 500 and code <= 522:
        return '🌧️☔'
    if code >= 600 and code <= 623:
        return '🌨️⛄'
    if code >= 700 and code <= 741:
        return '🌁🌫️'
    if code == 800:
        return '☀️😎'
    if code >= 801 and code <= 802:
        return '🌤️🌞'
    if code == 803:
        return '🌥️☁️'
    if code == 804:
        return '☁️☁️'
    if code == 900:
        return '🌧️🌧️'

def tmdbGetPoster(id, content_type='movie'):
    data_request = requests.get('{}{}/{}?api_key={}'.format(config.tmdb_main_api_url, content_type, id, config.tmdb_api_key))
    if data_request.status_code == requests.codes.ok:
        getFileFromURL('{}{}'.format(config.tmdb_poster_url, data_request.json()['poster_path']), f'{id}.jpeg')

def funnyCats():
    getFileFromURL("https://cataas.com/cat/gif", "cat.gif")
    telegramClient.sendFile('cat.gif')
    os.remove('cat.gif')