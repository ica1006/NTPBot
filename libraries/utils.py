import urllib
import requests
import os
from shutil import copyfileobj
from socket import socket
from time import sleep
from config import config
from clients.telegram_client import telegramClient


def bytesConversor(b):
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


def tmdbGetPoster(id, content_type='movie'):
    data_request = requests.get(
        '{}{}/{}?api_key={}'.format(config.tmdb_main_api_url, content_type, id, config.tmdb_api_key))
    if data_request.status_code == requests.codes.ok:
        getFileFromURL('{}{}'.format(config.tmdb_poster_url,
                       data_request.json()['poster_path']), f'{id}.jpeg')


def funnyCats():
    getFileFromURL("https://cataas.com/cat/gif", "cat.gif")
    telegramClient.sendFile('cat.gif')
    os.remove('cat.gif')


def pingHosts(max_connection_tries=config.max_connection_tries):
    services_down = list()
    message = ''
    for host in config.hosts:
        address = host['host']
        port = host['port']
        connection_socket = socket()
        connection_socket.settimeout(config.ping_timeout)
        for connection_try in range(1, max_connection_tries + 1):
            try:
                connection_socket.connect((address, port))
                break
            except:
                if connection_try == max_connection_tries:
                    services_down.append(host)
                else:
                    sleep(config.wait_time_between_tries)
            finally:
                connection_socket.close()

    if len(services_down) > 0:
        message = 'Servicio/s offline detectado,'
        for service in services_down:
            message += '\n{}'.format(service['name'])
            message += '\n{}:{} ❌'.format(service['host'], service['port'])
    else:
        message = 'Todos los servicios online ✅'

    return services_down, message
