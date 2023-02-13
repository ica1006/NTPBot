import requests, threading, qbittorrentapi, re, os, datetime, traceback, sys, geocoder, urllib, magichome
from config import config
from time import sleep
from fileinput import input
from proxmoxer import ProxmoxAPI
from dateutil import parser
from emojiflags.lookup import lookup
from socket import socket
from shutil import copyfileobj
from clients.telegram_client import telegramClient
from clients.logger import logger


stop_threads = False

class Main():

    def readMessagesThread(self):
        """Method that reads all the messages of the user in a new thread
        """
        while not stop_threads:
            try:
                messages = telegramClient.getMessages()
                if type(messages) is list:
                    nMessages = len(messages)
                    if nMessages > 0:
                        last_message = messages[nMessages - 1]['message']
                        if last_message['chat']['id'] == config.chat_id:
                            if 'text' in last_message:
                                logger.logEntry('message recipt: {}'.format(last_message['text']))
                                self.handleCommands(last_message['text'])
                            else:
                                logger.logEntry('message recipt, but there was not text detected')
                            telegramClient.setUpdateOffset(messages[nMessages - 1]['update_id'] + 1)
                sleep(config.message_read_delay)
            except Exception as e:
                logger.logEntry(f'Excepcion: {e}')
                logger.logEntry(traceback.format_exc())
                logger.logEntry(sys.exc_info()[2])
                telegramClient.incrementUpdateOffset()
                
    def handleCommands(self, command):
        """Method that handles user commands

        Args:
            command (string): user command
        """        
        if command.upper() == "HOLA":
            telegramClient.sendMessage("Hola, qué tal?")
        elif command.upper() == 'EMBY ACTUALIZADO?':
            self.embyUpToDate()
        elif command.upper() == 'EMBY ONLINE':
            self.embyOnlineUsers()
        elif re.search('QBITTORRENT [A-z]+', command.upper()):
            words = command.split()
            self.qbtGetFromState(words[1])
        elif command.upper() == 'PROXMOX ESTADO':
            self.pmxVmStatus()
        elif command.upper() == 'PING':
            self.pingHosts()
        elif command.upper() == 'TIEMPO':
            self.weatherRequestHandeler(config.weatherbit_default_pcode)
        elif re.search('TIEMPO( ([0-9]+|([A-z ]+(, [A-z]+)?)))?', command.upper()):
            words = command.split()
            words.pop(0)
            argument = ' '.join(words)
            self.weatherRequestHandeler(argument)
        elif command.upper() == 'SOLICITUDES':
            self.getPendingSolicitudes()
        elif command.upper() == 'RELOAD':
            config = Config('data.json')
            telegramClient.sendMessage('Config reloaded ⚙️')
        elif command.upper() == 'GATO':
            self.funnyCats()
        elif command.upper() == 'LEDS ON':
            controller = magichome.MagicHomeApi(config.mhome_led_ip, 0)
            controller.turn_on()
        elif command.upper() == 'LEDS OFF':
            controller = magichome.MagicHomeApi(config.mhome_led_ip, 0)
            controller.turn_off()
        else:
            telegramClient.sendMessage('Command not found')

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
        # https://media.ivan-cortes.es/Sessions?api_key=cf46d33d2363453fac9f093db3171ee5    
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
                        self.getFileFromURL(images_path[user], 'mainImage.jpeg')
                        telegramClient.sendPhoto('mainImage.jpeg')
                        os.remove('mainImage.jpeg')
            else:
                message = 'No hay ninguna sesión activa 🟡'
                telegramClient.sendMessage(message)

    def qbtGetFromState(self, state):
        """ Method that returns all the torrents from a specific state

        Args:
            state (string): state of the torrents
        """        
        if state != 'comprobando' and state != 'completados' and state != 'descargando' and state != 'error' and state != 'pausados' and state != 'subiendo':
            telegramClient.sendMessage('Estado de torrent no soportado')
            return

        qbtClient = qbittorrentapi.Client(host=config.qbtHost, username = config.qbtUser, password = config.qbtPass)
        torrents = list()
        
        # Add the specific torrents to the info list
        for torrent in qbtClient.torrents_info():
            if state == 'comprobando' and torrent.state_enum.is_checking:
                torrents.append(torrent.info)
            elif state == 'completados' and torrent.state_enum.is_complete:
                torrents.append(torrent.info)
            elif state == 'descargando' and torrent.state_enum.is_downloading:
                torrents.append(torrent.info)
            elif state == 'error' and torrent.state_enum.is_errored:
                torrents.append(torrent.info)
            elif state == 'pausados' and torrent.state_enum.is_paused:
                torrents.append(torrent.info)
            elif state == 'subiendo' and torrent.state_enum.is_uploading:
                torrents.append(torrent.info)
        
        telegramClient.sendMessage(f'Torrents en estado {state}:')
        message = ''
        torrentIndex = 0
        # From each torrent, it takes the name and the index. If it is downloading,
        # it takes more info, like the downloaded %, eta, download speed, etc
        for torrent in torrents:
            torrentIndex += 1
            message += '{}, {}/{}\n'.format(torrent['name'], torrentIndex, len(torrents))
            if state == 'descargando':
                percent = torrent['completed'] / torrent['size'] * 100
                eta = torrent['eta']
                dlspeed = self.bytesConversor(torrent['dlspeed'])
                if eta >= 604800:
                    eta = '♾️'
                else:
                    eta = str(datetime.timedelta(seconds=eta))
                message += '{:.2f}% '.format(percent)
                if percent < 40 and eta != '♾️':
                    message += '🟠  '
                elif percent >= 40 and percent < 60 and eta != '♾️':
                    message += '🟡  '
                elif percent >= 60 and percent < 80 and eta != '♾️':
                    message += '🔵  '
                elif percent >= 80 and eta != '♾️':
                    message += '🟢  '
                elif eta == '♾️':
                    message += '🔴  '
                message += f'{dlspeed}/s\n'
                message += 'ETA = {} ⏱️\n'.format(eta)
            message += '\n'
        telegramClient.sendMessage(message)

    def pmxVmStatus(self):
        proxmox = ProxmoxAPI(config.pmx_host, user=config.pmx_user, password=config.pmx_pass, verify_ssl=False)
        for vm in config.vms:
            message = ''
            global_status = proxmox.nodes('pve').qemu(vm).get('status/current')
            status = global_status['status']
            if status == 'running':
                status += ' ✅'
            else:
                status += ' ❌'

            if status == 'running ✅':
                actual_status = proxmox.nodes('pve').qemu(vm).get('rrddata?timeframe=hour')[0]
                cpu = actual_status['cpu'] * 100

                used_mem = self.bytesConversor(actual_status['mem'])
                max_mem = self.bytesConversor(actual_status['maxmem'])
                used_mem_p = actual_status['mem'] / actual_status['maxmem'] * 100
                
                uptime = str(datetime.timedelta(seconds=global_status['uptime']))
                disk_space = self.bytesConversor(global_status['maxdisk'])

                disk_wr = '{}/s'.format(self.bytesConversor(actual_status['diskwrite']))
                disk_rd = '{}/s'.format(self.bytesConversor(actual_status['diskread']))

                net_in = '{}/s'.format(self.bytesConversor(actual_status['netin']))
                net_out = '{}/s'.format(self.bytesConversor(actual_status['netout']))

                cpu_emoji = self.percentToEmoji(cpu)
                ram_emoji = self.percentToEmoji(used_mem_p)

                message += '{} 💻\n'.format(global_status['name'])
                message += 'Status: {}\n'.format(status)
                message += 'CPU: {:.2f}% {}\n'.format(cpu, cpu_emoji)
                message += 'RAM: {}/{}\n          {:.2f}% {}\n'.format(used_mem, max_mem, used_mem_p, ram_emoji)
                message += 'Uptime: {}\n\n'.format(uptime)
                message += 'Boot Drive: {} 💾\n  Write: {}\n  Read: {}\n\n'.format(disk_space, disk_wr, disk_rd)
                message += 'Network 🌐\n  In: {}\n  Out: {}\n\n'.format(net_in, net_out)
            else:
                message += '{} 💻\n'.format(global_status['name'])
                message += 'Status: {}\n'.format(status)
            telegramClient.sendMessage(message)
    
    def percentToEmoji(self,percent):
        if percent > 0 and percent < 30:
            return '🟢'
        if percent >= 30 and percent < 60:
            return '🟡'
        if percent >= 60 and percent < 90:
            return '🟠'
        if percent >= 90:
            return '🔴'
        return '⚪'

    def bytesConversor (self,b):
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
    
    def pingHosts(self, thread = False):
        anyException = False
        serviceDown = list()
        message = ''
        for host in config.hosts:
            address = host['host']
            port = host['port']
            s = socket()
            s.settimeout(config.ping_timeout)
            try:
                s.connect((address, port))
            except:
                try:
                    sleep(10)
                    s.connect((address, port))
                except Exception as e:
                    anyException = True
                    serviceDown.append(f'{address}:{port}')
                    print(e)
                    message = 'Servicio offline detectado,'
                    if 'name' in host:
                        message += '\n{}'.format(host['name'])
                    message += f'\n{address}:{port} ❌'
                    if thread is False:
                        telegramClient.sendMessage(message)
            finally:
                s.close()
        if anyException is False and thread is False:
            telegramClient.sendMessage('Todos los servicios online ✅')
        return not anyException, serviceDown, message
    
    def pingHost_Thread (self):
        down_services = list()
        while stop_threads is False:
            up, services, message = self.pingHosts(thread=True)
            if up is False:
                for service in services:
                    if service not in down_services:
                        telegramClient.sendMessage(message)
                        down_services.append(service)
            elif len(down_services) != 0:
                telegramClient.sendMessage(f'Todos los servicios han vuelto a estar operativos ✅')
                down_services.clear()

            sleep(config.time_between_comprobations)

    def getWeather(self, request):
        rq = requests.get(request)
        if rq.status_code == requests.codes.ok:
            data = rq.json()['data'][0]
            code = data['weather']['code']
            description = data['weather']['description']
            city_name = data['city_name']
            country_code = data['country_code']
            wind_spd = data['wind_spd']
            wind_dir = data['wind_cdir_full']
            temp = data['temp']
            temp_feels_like = data['app_temp']
            cloud_percentage = data['clouds']
            humidity_percentage = data['rh']
            precip = data['precip']

            message = f'{city_name} {lookup(country_code)}\n'
            message += f'{self.weatherEmoji(code)} {description}\n'
            message += '🌡️ {:.2f}º, se siente como {:.2f}º\n'.format(temp, temp_feels_like)
            message += 'Viento: {:.2f}m/s {}\n'.format(wind_spd, wind_dir)
            message += 'Nubes: {:.2f}%\n'.format(cloud_percentage)
            message += 'Precipitaciones: {:.2f}\n'.format(precip)
            message += '{:.2f}% de humedad\n'.format(humidity_percentage)
            telegramClient.sendMessage(message)
        else:
            telegramClient.sendMessage('No se ha podido obtener el tiempo')
    
    def weatherRequestHandeler(self, argument):
        if re.search('[0-9]+', argument.upper()):
            request = '{}&postal_code={}&country={}'.format(config.weatherbit_url, argument, config.weatherbit_api_country)
            self.getWeather(request)
        elif re.search('[A-z ]+(, [A-z]+).', argument.upper()):
            arguments = argument.split(', ')
            request = '{}&city={}&country={}'.format(config.weatherbit_url, arguments[0], arguments[1])
            print(request)
            self.getWeather(request)
        elif re.search('[A-z ]+', argument.upper()):
            request = '{}&city={}'.format(config.weatherbit_url, argument)
            self.getWeather(request)

    def weatherEmoji(self, code):
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

    def getPendingSolicitudes(self, print=True):
        headers = {
            'X-Api-Key': config.overseerr_api_key
        }

        rq = requests.get(url='{}{}'.format(config.overseerr_url, 'request'), headers=headers)
        if rq.status_code == requests.codes.ok:
            data = rq.json()
            results = data['results']
            if print is True:
                for result in results:
                    self.getSingleSolicitude(result)
            return results
    
    def getSingleSolicitude(self, solicitude):
        type = solicitude['media']['mediaType']
        tmdb_id = solicitude['media']['tmdbId']
        self.tmdbGetPoster(id=tmdb_id, type=type)
        telegramClient.sendPhoto(f'{tmdb_id}.jpeg')
        os.remove(f'{tmdb_id}.jpeg')

        tmdb_data = requests.get('{}{}/{}?api_key={}&language={}'.format(config.tmdb_main_api_url, type, tmdb_id, config.tmdb_api_key, config.tmdb_lang))
        if tmdb_data.status_code == requests.codes.ok:
            if type == 'movie':
                tmdb_data = tmdb_data.json()
                message = tmdb_data['title']
                message += '\n({})\n'.format(tmdb_data['original_title'])
                message += '{} 📆\n'.format(tmdb_data['release_date'])
                message += '{:.2f}/10 ⭐\n'.format(tmdb_data['vote_average'])
                message += 'Type: {}'.format(type)
                message += '\n\n{}'.format(tmdb_data['overview'])
                telegramClient.sendMessage(message)
            elif type == 'tv':
                tmdb_data = tmdb_data.json()
                message = tmdb_data['name']
                message += '\n({})\n'.format(tmdb_data['original_name'])
                message += '{} 📆\n'.format(tmdb_data['first_air_date'])
                message += '{:.2f}/10 ⭐\n'.format(tmdb_data['vote_average'])
                message += 'Type: {}\n'.format(type)
                message += 'Seasons:\n  '
                for season in solicitude['seasons']:
                    message += '{} '.format(season['seasonNumber'])
                message += '\n\n{}'.format(tmdb_data['overview'])
                telegramClient.sendMessage(message)

    def solicitudesThread(self):
        current_solicitudes = list()

        for result in self.getPendingSolicitudes(print=False):
            current_solicitudes.append(result['id'])
        
        while not stop_threads:
            try:
                solicitudes = self.getPendingSolicitudes(print=False)
                for result in solicitudes:
                    if result['id'] not in current_solicitudes:
                        telegramClient.sendMessage('Nueva solicitud detectada')
                        current_solicitudes.append(result['id'])
                        self.getSingleSolicitude(result)
            except:
                pass
            sleep(10)

    def tmdbGetPoster(self, id, type='movie'):
        data_request = requests.get('{}{}/{}?api_key={}'.format(config.tmdb_main_api_url, type, id, config.tmdb_api_key))
        if data_request.status_code == requests.codes.ok:
            self.getFileFromURL('{}{}'.format(config.tmdb_poster_url, data_request.json()['poster_path']), f'{id}.jpeg')

    def funnyCats(self):
        self.getFileFromURL("https://cataas.com/cat/gif", "cat.gif")
        telegramClient.sendFile('cat.gif')
        os.remove('cat.gif')

    def getFileFromURL(self, url, filename):
        try:
            urllib.request.urlretrieve(url, filename)
        except:
            photo_rq = requests.get(url, stream=True)
            with open(filename, 'wb') as out_file:
                copyfileobj(photo_rq.raw, out_file)
            del photo_rq

if __name__ == '__main__':
    main = Main()
    logger.logEntry('Bot starting in 3 seconds.')
    logger.logEntry('Write \'exit\' to exit')
    sleep(3)
    print('')

    logger.logEntry('Bot started')
    reading = threading.Thread(target=main.readMessagesThread)
    reading.start()
    logger.logEntry('Reading thread started')
    host_comprobation = threading.Thread(target=main.pingHost_Thread)
    host_comprobation.start()
    logger.logEntry('Host comprobation thread started')
    solicitudes_thread = threading.Thread(target=main.solicitudesThread)
    solicitudes_thread.start()
    logger.logEntry('Solicitudes thread started')

    for line in input():
        if line.rstrip().upper() == 'EXIT':
            stop_threads = True
            reading.join()
            host_comprobation.join()
            solicitudes_thread.join()
            break
        else: 
            logger.logEntry('stdin not recognized')
    