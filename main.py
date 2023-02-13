import requests, threading, qbittorrentapi, re, os, datetime, traceback, sys, magichome
from config import config
from time import sleep
from fileinput import input
from proxmoxer import ProxmoxAPI
from emojiflags.lookup import lookup
from socket import socket
from utils import getFileFromURL, bytesConversor, percentToEmoji, weatherEmoji
from clients.telegram_client import telegramClient
from clients.logger import logger
from clients.emby_client import embyClient
from clients.qbittorrent_client import qbittorentClient


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
            embyClient.embyUpToDate()
        elif command.upper() == 'EMBY ONLINE':
            embyClient.embyOnlineUsers()
        elif re.search('QBITTORRENT [A-z]+', command.upper()):
            words = command.split()
            qbittorentClient.qbtGetFromState(words[1])
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
            config.reload()
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

                used_mem = bytesConversor(actual_status['mem'])
                max_mem = bytesConversor(actual_status['maxmem'])
                used_mem_p = actual_status['mem'] / actual_status['maxmem'] * 100
                
                uptime = str(datetime.timedelta(seconds=global_status['uptime']))
                disk_space = bytesConversor(global_status['maxdisk'])

                disk_wr = '{}/s'.format(bytesConversor(actual_status['diskwrite']))
                disk_rd = '{}/s'.format(bytesConversor(actual_status['diskread']))

                net_in = '{}/s'.format(bytesConversor(actual_status['netin']))
                net_out = '{}/s'.format(bytesConversor(actual_status['netout']))

                cpu_emoji = percentToEmoji(cpu)
                ram_emoji = percentToEmoji(used_mem_p)

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
            message += f'{weatherEmoji(code)} {description}\n'
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
        self.tmdbGetPoster(id=tmdb_id, content_type=type)
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

    def tmdbGetPoster(self, id, content_type='movie'):
        data_request = requests.get('{}{}/{}?api_key={}'.format(config.tmdb_main_api_url, content_type, id, config.tmdb_api_key))
        if data_request.status_code == requests.codes.ok:
            getFileFromURL('{}{}'.format(config.tmdb_poster_url, data_request.json()['poster_path']), f'{id}.jpeg')

    def funnyCats(self):
        getFileFromURL("https://cataas.com/cat/gif", "cat.gif")
        telegramClient.sendFile('cat.gif')
        os.remove('cat.gif')

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
    