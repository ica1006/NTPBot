import qbittorrentapi, datetime
from clients.telegram_client import telegramClient
from config import config
from lang import lang
from libraries.utils import bytesConversor

class QBittorentClient():

    def qbtGetFromState(self, state):
        """ Method that returns all the torrents from a specific state

        Args:
            state (string): state of the torrents
        """        
        #if state != 'comprobando' and state != 'completados' and state != 'descargando' and state != 'error' and state != 'pausados' and state != 'subiendo':
        if state not in list(lang.qbittorrent_messages['states'].values()):
            telegramClient.sendMessage('Estado de torrent no soportado')
            return

        qbtClient = qbittorrentapi.Client(host=config.qbtHost, username = config.qbtUser, password = config.qbtPass)
        torrents = list()
        
        # Add the specific torrents to the info list
        for torrent in qbtClient.torrents_info():
            if state == lang.qbittorrent_messages['states']['checking'] and torrent.state_enum.is_checking:
                torrents.append(torrent.info)
            elif state == lang.qbittorrent_messages['states']['completed'] and torrent.state_enum.is_complete:
                torrents.append(torrent.info)
            elif state == lang.qbittorrent_messages['states']['downloading'] and torrent.state_enum.is_downloading:
                torrents.append(torrent.info)
            elif state == lang.qbittorrent_messages['states']['error'] and torrent.state_enum.is_errored:
                torrents.append(torrent.info)
            elif state == lang.qbittorrent_messages['states']['paused'] and torrent.state_enum.is_paused:
                torrents.append(torrent.info)
            elif state == lang.qbittorrent_messages['states']['uploading'] and torrent.state_enum.is_uploading:
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
                dlspeed = bytesConversor(torrent['dlspeed'])
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

qbittorentClient = QBittorentClient()