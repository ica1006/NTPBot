import requests, os, geocoder
from dateutil import parser
from config import config
from clients.telegram_client import telegramClient
from libraries.emojiflags.lookup import lookup
from libraries.utils import getFileFromURL

class EmbyClient():

    def embyUpToDate(self):
        """ Method that responds to 'Emby actualizado?' command.
            It checks if the emby server is up to date
        """        
        rq = requests.get(f'{config.emby_base_url}System/Info?api_key={config.emby_api_key}')
        if rq.status_code == requests.codes.ok:
            data = rq.json()
            if data['HasUpdateAvailable'] == True:
                telegramClient.sendMessage("Actualización disponible! ⏱️")
            else:
                telegramClient.sendMessage("Emby está actualizado ✅")
        else:
            telegramClient.sendMessage('Emby no responde ❌')

    def embyOnlineUsers(self):
        """ Method that responds to 'Emby online' command.
            It checks emby online sessions.
        """    
        rq = requests.get(f'{config.emby_base_url}Sessions?api_key={config.emby_api_key}')
        if rq.status_code == requests.codes.ok:
            sessions = rq.json()
            nSessions = len(sessions)
            userSessions = dict()
            images_path = dict()
            dates = dict()
            ips = dict()
            devices = dict()

            if nSessions > 0:
                for session in sessions:
                    if 'UserName' in session and session['UserName'] not in userSessions:
                        userSessions[session['UserName']] = None
                        dates[session['UserName']] = parser.parse(session['LastActivityDate']).strftime('%H:%M:%S  \n    %d/%m/%y')
                        dates[session['UserName']] = dates[session['UserName']].replace(' ', '🕑', 1)
                        ips[session['UserName']] = session['RemoteEndPoint']
                        devices[session['UserName']] = session['DeviceName']
                        if session['Client'] == 'Emby for Android':
                            devices[session['UserName']] += '\n    Android 🤖'
                        elif session['Client'] == 'Emby for iOS':
                            devices[session['UserName']] += '\n    iOS 🍏'
                        elif session['Client'] == 'Emby Web':
                            devices[session['UserName']] += '\n    Web 🌐'
                        elif session['Client'] == 'Emby for Apple Watch':
                            devices[session['UserName']] += '\n    Apple Watch ⌚'
                        
                    if 'NowPlayingItem' in session and 'FileName' in session['NowPlayingItem']:
                        userSessions[session['UserName']] = '{}, codec {}'.format(session['NowPlayingItem']['FileName'], session['NowPlayingItem']['MediaStreams'][0]['Codec'])
                        if not session['NowPlayingItem']['Id'] is None and session['NowPlayingItem']['Id'] != '' and session['UserName'] not in images_path:
                            images_path[session['UserName']] = '{}Items/{}/Images/Primary?api_key={}'.format(config.emby_base_url, session['NowPlayingItem']['Id'], config.emby_api_key)
                    elif 'NowPlayingItem' in session and 'Name' in session['NowPlayingItem']:
                        userSessions[session['UserName']] = '{}, codec {}'.format(session['NowPlayingItem']['Name'], session['NowPlayingItem']['MediaStreams'][0]['Codec'])
                        if not session['NowPlayingItem']['Id'] is None and session['NowPlayingItem']['Id'] != '' and session['UserName'] not in images_path:
                            images_path[session['UserName']] = '{}Items/{}/Images/Primary?api_key={}'.format(config.emby_base_url, session['NowPlayingItem']['Id'], config.emby_api_key)

            if len(userSessions) > 0:
                message = f'{len(userSessions)} sesiones activas 🟢\n'
                transmissions = dict()
                for user in list(userSessions.keys()):
                    message += '  {} 🧑🏼‍🦲\n    {} 🗓️\n    IP: {}\n    {},\n    {} {}\n    {}\n\n'.format(user, dates[user], ips[user], geocoder.ip(ips[user]).city, 
                            geocoder.ip(ips[user]).state, lookup(geocoder.ip(ips[user]).country), devices[user])
                    if not userSessions[user] is None:
                        transmissions[user] = f'{user} viendo {userSessions[user]}\n'
                telegramClient.sendMessage(message)

                for user in list(userSessions.keys()):
                    if user in transmissions:
                        telegramClient.sendMessage(transmissions[user])

                    if user in images_path:
                        getFileFromURL(url=images_path[user], filename='mainImage.jpeg')
                        telegramClient.sendPhoto('mainImage.jpeg')
                        os.remove('mainImage.jpeg')
            else:
                message = 'No hay ninguna sesión activa 🟡'
                telegramClient.sendMessage(message)

embyClient = EmbyClient()