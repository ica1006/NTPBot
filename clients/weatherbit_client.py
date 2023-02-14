import requests
import re
from libraries.emojiflags.lookup import lookup
from config import config
from clients.telegram_client import telegramClient


class WeatherbitClient():
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
            message += '🌡️ {:.2f}º, se siente como {:.2f}º\n'.format(
                temp, temp_feels_like)
            message += 'Viento: {:.2f}m/s {}\n'.format(wind_spd, wind_dir)
            message += 'Nubes: {:.2f}%\n'.format(cloud_percentage)
            message += 'Precipitaciones: {:.2f}\n'.format(precip)
            message += '{:.2f}% de humedad\n'.format(humidity_percentage)
            telegramClient.sendMessage(message)
        else:
            telegramClient.sendMessage('No se ha podido obtener el tiempo')

    def weatherRequestHandeler(self, argument):
        if re.search('[0-9]+', argument.upper()):
            request = '{}&postal_code={}&country={}'.format(
                config.weatherbit_url, argument, config.weatherbit_api_country)
            self.getWeather(request)
        elif re.search('[A-z ]+(, [A-z]+).', argument.upper()):
            arguments = argument.split(', ')
            request = '{}&city={}&country={}'.format(
                config.weatherbit_url, arguments[0], arguments[1])
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


weatherbitClient = WeatherbitClient()
