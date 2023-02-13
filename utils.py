import urllib, requests
from shutil import copyfileobj

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