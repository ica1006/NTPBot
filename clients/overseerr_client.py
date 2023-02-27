import requests, os
from clients.telegram_client import telegramClient
from config import config
from time import sleep
from libraries.utils import tmdbGetPoster

class OverseerrClient():

    def getPendingSolicitudes(self, print_solicitudes=True, request_filter='unavailable'):
        headers = {
            'X-Api-Key': config.overseerr_api_key
        }

        rq = requests.get(url='{}{}?take=9999&filter={}'.format(config.overseerr_url, 'request', request_filter), headers=headers)
        if rq.status_code == requests.codes.ok:
            data = rq.json()
            results = data['results']
            if print_solicitudes is True:
                for result in results:
                    self.getSingleSolicitude(result)
                    sleep(0.5)
            return results
    
    def getSingleSolicitude(self, solicitude):
        content_type = solicitude['media']['mediaType']
        tmdb_id = solicitude['media']['tmdbId']
        tmdbGetPoster(id=tmdb_id, content_type=content_type)
        telegramClient.sendPhoto(f'{tmdb_id}.jpeg')
        os.remove(f'{tmdb_id}.jpeg')

        tmdb_data = requests.get('{}{}/{}?api_key={}&language={}'.format(config.tmdb_main_api_url, content_type, tmdb_id, config.tmdb_api_key, config.tmdb_lang))
        if tmdb_data.status_code == requests.codes.ok:
            if content_type == 'movie':
                tmdb_data = tmdb_data.json()
                message = tmdb_data['title']
                message += '\n({})\n'.format(tmdb_data['original_title'])
                message += '{} 📆\n'.format(tmdb_data['release_date'])
                message += '{:.2f}/10 ⭐\n'.format(tmdb_data['vote_average'])
                message += 'Type: {}'.format(content_type)
                message += '\n\n{}'.format(tmdb_data['overview'])
                telegramClient.sendMessage(message)
            elif content_type == 'tv':
                tmdb_data = tmdb_data.json()
                message = tmdb_data['name']
                message += '\n({})\n'.format(tmdb_data['original_name'])
                message += '{} 📆\n'.format(tmdb_data['first_air_date'])
                message += '{:.2f}/10 ⭐\n'.format(tmdb_data['vote_average'])
                message += 'Type: {}\n'.format(content_type)
                message += 'Seasons:\n  '
                for season in solicitude['seasons']:
                    message += '{} '.format(season['seasonNumber'])
                message += '\n\n{}'.format(tmdb_data['overview'])
                telegramClient.sendMessage(message)

overseerrClient = OverseerrClient()