import requests, threading, logging, qbittorrentapi, re, os, datetime, traceback, sys, geocoder, urllib, magichome
from time import sleep
from fileinput import input
from proxmoxer import ProxmoxAPI
from dateutil import parser
from emojiflags.lookup import lookup
from socket import socket
from shutil import copyfileobj
from models.config import Config


stop_threads = False


def logEntry(entry):
    """ Method that logs actions into the file

    Args:
        entry (string): log entry
    """    
    logging.info(entry)
    print(entry)


class Main():

    config = Config('data.json')

    def readMessages(self):
        """Method that reads all the messages of the user in a new thread
        """        
        update_offset = 1
        while not stop_threads:
            try:
                rq = requests.get(f'{self.config.telegram_base_url}getUpdates?offset={update_offset}')
                if rq.status_code == requests.codes.ok:
                    data = rq.json()
                    messages = data['result']
                    nMessages = len(messages)
                    if nMessages > 0:
                        last_message = messages[nMessages - 1]['message']
                        if last_message['chat']['id'] == self.config.chat_id:
                            if 'text' in last_message:
                                logEntry('message recipt: {}'.format(last_message['text']))
                                self.handleCommands(last_message['text'])
                            else:
                                logEntry('message recipt, but there was not text detected')
                            update_offset = messages[nMessages - 1]['update_id'] + 1
                sleep(self.config.message_read_delay)
            except Exception as e:
                logEntry(f'Excepcion: {e}')
                logEntry(traceback.format_exc())
                logEntry(sys.exc_info()[2])
                update_offset += 1
                
    def handleCommands(self, command):
        """Method that handles user commands

        Args:
            command (string): user command
        """        
        if command.upper() == "HOLA":
            self.sendMessage("Hola, qué tal?")
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
            self.weatherRequestHandeler(self.config.weatherbit_default_pcode)
        elif re.search('TIEMPO( ([0-9]+|([A-z ]+(, [A-z]+)?)))?', command.upper()):
            words = command.split()
            words.pop(0)
            argument = ' '.join(words)
            self.weatherRequestHandeler(argument)
        elif command.upper() == 'SOLICITUDES':
            self.getPendingSolicitudes()
        elif command.upper() == 'RELOAD':
            self.config = Config('data.json')
            self.sendMessage('Config reloaded ⚙️')
        elif command.upper() == 'GATO':
            self.funnyCats()
        elif command.upper() == 'LEDS ON':
            controller = magichome.MagicHomeApi(self.config.mhome_led_ip, 0)
            controller.turn_on()
        elif command.upper() == 'LEDS OFF':
            controller = magichome.MagicHomeApi(self.config.mhome_led_ip, 0)
            controller.turn_off()
        else:
            self.sendMessage('Command not found')

    def embyUpToDate(self):
        """ Method that responds to 'Emby actualizado?' command.
            It checks if the emby server is up to date
        """        
        rq = requests.get(f'{self.config.emby_base_url}System/Info?api_key={self.config.emby_api_key}')
        if rq.status_code == requests.codes.ok:
            data = rq.json()
            if data['HasUpdateAvailable'] == True:
                self.sendMessage("Actualización disponible! ⏱️")
            else:
                self.sendMessage("Emby está actualizado ✅")
        else:
            self.sendMessage('Emby no responde ❌')

    def embyOnlineUsers(self):
        """ Method that responds to 'Emby online' command.
            It checks emby online sessions.
        """    
        # https://media.ivan-cortes.es/Sessions?api_key=cf46d33d2363453fac9f093db3171ee5    
        rq = requests.get(f'{self.config.emby_base_url}Sessions?api_key={self.config.emby_api_key}')
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
                            images_path[session['UserName']] = '{}Items/{}/Images/Primary?api_key={}'.format(self.config.emby_base_url, session['NowPlayingItem']['Id'], self.config.emby_api_key)
                    elif 'NowPlayingItem' in session and 'Name' in session['NowPlayingItem']:
                        userSessions[session['UserName']] = '{}, codec {}'.format(session['NowPlayingItem']['Name'], session['NowPlayingItem']['MediaStreams'][0]['Codec'])
                        if not session['NowPlayingItem']['Id'] is None and session['NowPlayingItem']['Id'] != '' and session['UserName'] not in images_path:
                            images_path[session['UserName']] = '{}Items/{}/Images/Primary?api_key={}'.format(self.config.emby_base_url, session['NowPlayingItem']['Id'], self.config.emby_api_key)

            if len(userSessions) > 0:
                message = f'{len(userSessions)} sesiones activas 🟢\n'
                transmissions = dict()
                for user in list(userSessions.keys()):
                    message += '  {} 🧑🏼‍🦲\n    {} 🗓️\n    IP: {}\n    {},\n    {} {}\n    {}\n\n'.format(user, dates[user], ips[user], geocoder.ip(ips[user]).city, 
                            geocoder.ip(ips[user]).state, lookup(geocoder.ip(ips[user]).country), devices[user])
                    if not userSessions[user] is None:
                        transmissions[user] = f'{user} viendo {userSessions[user]}\n'
                self.sendMessage(message)

                for user in list(userSessions.keys()):
                    if user in transmissions:
                        self.sendMessage(transmissions[user])

                    if user in images_path:
                        self.getFileFromURL(images_path[user], 'mainImage.jpeg')
                        self.sendPhoto('mainImage.jpeg')
                        os.remove('mainImage.jpeg')
            else:
                message = 'No hay ninguna sesión activa 🟡'
                self.sendMessage(message)

    def qbtGetFromState(self, state):
        """ Method that returns all the torrents from a specific state

        Args:
            state (string): state of the torrents
        """        
        if state != 'comprobando' and state != 'completados' and state != 'descargando' and state != 'error' and state != 'pausados' and state != 'subiendo':
            self.sendMessage('Estado de torrent no soportado')
            return

        qbtClient = qbittorrentapi.Client(host=self.config.qbtHost, username = self.config.qbtUser, password = self.config.qbtPass)
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
        
        self.sendMessage(f'Torrents en estado {state}:')
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
        self.sendMessage(message)

    def pmxVmStatus(self):
        proxmox = ProxmoxAPI(self.config.pmx_host, user=self.config.pmx_user, password=self.config.pmx_pass, verify_ssl=False)
        for vm in self.config.vms:
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
            self.sendMessage(message)
    
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

    def sendFile(self, filePath):
        """ Method that sends a file to the telegram conversation

        Args:
            filePath (string): file path
        """        
        file = open(filePath, 'rb')
        file_bytes = file.read()
        file.close()
        response = {
            'document': (file.name, file_bytes)
        }
        requests.post(url=f'{self.config.telegram_base_url}sendDocument?chat_id={self.config.chat_id}', files=response)
        logEntry(f'File {file.name} send')

    def sendPhoto(self, filePath):
        img = open(filePath, 'rb')
        rq = requests.post(f'{self.config.telegram_base_url}sendPhoto?chat_id={self.config.chat_id}', files={'photo':img})
        img.close()
        if rq.status_code == requests.codes.ok:
            logEntry(f'Photo sent')
        else:
            logEntry('Error while sending the photo')
    
    def sendMessage(self, message):
        """ Method that sends a message to the user

        Args:
            message (string): message to be send
        """        
        if len(message) < 4096:
            rq = requests.get(f'{self.config.telegram_base_url}sendMessage?chat_id={self.config.chat_id}&text={message}')
            if rq.status_code == requests.codes.ok:
                logEntry(f'message sent: {message}')
            else:
                logEntry(f'error while sending message {message}')
                logEntry(rq)
        else:
            textFile = open('message.txt', 'w')
            textFile.write(message)
            textFile.close()
            self.sendFile('message.txt')
            os.remove('message.txt')

    def pingHosts(self, thread = False):
        anyException = False
        serviceDown = list()
        message = ''
        for host in self.config.hosts:
            address = host['host']
            port = host['port']
            s = socket()
            s.settimeout(self.config.ping_timeout)
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
                        self.sendMessage(message)
            finally:
                s.close()
        if anyException is False and thread is False:
            self.sendMessage('Todos los servicios online ✅')
        return not anyException, serviceDown, message
    
    def pingHost_Thread (self):
        down_services = list()
        while stop_threads is False:
            up, services, message = self.pingHosts(thread=True)
            if up is False:
                for service in services:
                    if service not in down_services:
                        self.sendMessage(message)
                        down_services.append(service)
            elif len(down_services) != 0:
                self.sendMessage(f'Todos los servicios han vuelto a estar operativos ✅')
                down_services.clear()

            sleep(self.config.time_between_comprobations)

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
            self.sendMessage(message)
        else:
            self.sendMessage('No se ha podido obtener el tiempo')
    
    def weatherRequestHandeler(self, argument):
        if re.search('[0-9]+', argument.upper()):
            request = '{}&postal_code={}&country={}'.format(self.config.weatherbit_url, argument, self.config.weatherbit_api_country)
            self.getWeather(request)
        elif re.search('[A-z ]+(, [A-z]+).', argument.upper()):
            arguments = argument.split(', ')
            request = '{}&city={}&country={}'.format(self.config.weatherbit_url, arguments[0], arguments[1])
            print(request)
            self.getWeather(request)
        elif re.search('[A-z ]+', argument.upper()):
            request = '{}&city={}'.format(self.config.weatherbit_url, argument)
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
            'X-Api-Key': self.config.overseerr_api_key
        }

        rq = requests.get(url='{}{}'.format(self.config.overseerr_url, 'request'), headers=headers)
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
        self.sendPhoto(f'{tmdb_id}.jpeg')
        os.remove(f'{tmdb_id}.jpeg')

        tmdb_data = requests.get('{}{}/{}?api_key={}&language={}'.format(self.config.tmdb_main_api_url, type, tmdb_id, self.config.tmdb_api_key, self.config.tmdb_lang))
        if tmdb_data.status_code == requests.codes.ok:
            if type == 'movie':
                tmdb_data = tmdb_data.json()
                message = tmdb_data['title']
                message += '\n({})\n'.format(tmdb_data['original_title'])
                message += '{} 📆\n'.format(tmdb_data['release_date'])
                message += '{:.2f}/10 ⭐\n'.format(tmdb_data['vote_average'])
                message += 'Type: {}'.format(type)
                message += '\n\n{}'.format(tmdb_data['overview'])
                self.sendMessage(message)
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
                self.sendMessage(message)

    def solicitudesThread(self):
        current_solicitudes = list()

        for result in self.getPendingSolicitudes(print=False):
            current_solicitudes.append(result['id'])
        
        while not stop_threads:
            try:
                solicitudes = self.getPendingSolicitudes(print=False)
                for result in solicitudes:
                    if result['id'] not in current_solicitudes:
                        self.sendMessage('Nueva solicitud detectada')
                        current_solicitudes.append(result['id'])
                        self.getSingleSolicitude(result)
            except:
                pass
            sleep(10)

    def tmdbGetPoster(self, id, type='movie'):
        data_request = requests.get('{}{}/{}?api_key={}'.format(self.config.tmdb_main_api_url, type, id, self.config.tmdb_api_key))
        if data_request.status_code == requests.codes.ok:
            self.getFileFromURL('{}{}'.format(self.config.tmdb_poster_url, data_request.json()['poster_path']), f'{id}.jpeg')

    def funnyCats(self):
        self.getFileFromURL("https://cataas.com/cat/gif", "cat.gif")
        self.sendFile('cat.gif')
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
    logging.basicConfig(handlers=[logging.FileHandler(filename="log.txt", encoding='utf-8', mode='w')], level=logging.INFO, format='%(asctime)s - %(message)s')
    main = Main()
    logEntry('Bot starting in 3 seconds.')
    logEntry('Write \'exit\' to exit')
    sleep(3)
    print('')

    logEntry('Bot started')
    reading = threading.Thread(target=main.readMessages)
    reading.start()
    logEntry('Reading thread started')
    host_comprobation = threading.Thread(target=main.pingHost_Thread)
    host_comprobation.start()
    logEntry('Host comprobation thread started')
    solicitudes_thread = threading.Thread(target=main.solicitudesThread)
    solicitudes_thread.start()
    logEntry('Solicitudes thread started')

    for line in input():
        if line.rstrip().upper() == 'EXIT':
            stop_threads = True
            reading.join()
            host_comprobation.join()
            solicitudes_thread.join()
            break
        else: 
            logEntry('stdin not recognized')
    