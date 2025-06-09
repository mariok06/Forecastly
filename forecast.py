from dotenv import load_dotenv
from datetime import datetime
import plotly.express as px
from flask import flash
import pandas as pd
import requests
import logging
import pytz
import os


load_dotenv()

API_KEY = os.getenv('OPENWEATHER_API_KEY')
COUNTRY_CODE = 'IND'
icon_dict = {'11d': '⛈️', '11n': '⛈️', '09d': '🌦️', '09n': '🌧️', '10d': '🌦️', '10n': '🌧️', '13d': '❄️', '13n': '❄️',
             '50d': '🌫️', '50n': '🌫️', '01d': '☀️', '01n': '⭐', '02d': '🌥️', '02n': '🌙', '03d': '☁️', '03n': '☁️',
             '04d': '☁️', '04n': '☁️', }

class Forecast:
    def __init__(self):
        self.lat = 0
        self.lon = 0


    def get_coords(self, city):
        coords_response = requests.get(f'http://api.openweathermap.org/geo/1.0/direct?q={city},{COUNTRY_CODE}&appid={API_KEY}')
        coords_data = coords_response.json()
        self.lat = coords_data[0]['lat']
        self.lon= coords_data[0]['lon']

        return self.lat, self.lon


    def curr_weather_data(self, city):
        lat, lon = self.get_coords(city)
        weather_params = {
            'lat': lat,
            'lon': lon,
            'appid': API_KEY,
            'units': 'metric',
        }

        try:
            weather_response = requests.get(url='https://api.openweathermap.org/data/2.5/weather', params=weather_params)
            data = weather_response.json()

            if data.get('cod') == 404:
                flash('City Not Found. Please check the spelling.')

            else:
                icon = data['weather'][0]['icon']
                curr_temp = data['main']['temp']
                feels_like = data['main']['feels_like']
                pressure = data['main']['pressure']
                humidity = data['main']['humidity']
                visibility = data['visibility']
                wind_speed = data['wind']['speed']
                sunrise_ts = data['sys']['sunrise']
                sunset_ts = data['sys']['sunset']

                india = pytz.timezone('Asia/Kolkata')

                sunrise_local = datetime.fromtimestamp(sunrise_ts).astimezone(india)
                sunset_local = datetime.fromtimestamp(sunset_ts).astimezone(india)

                sunrise = sunrise_local.strftime('%I:%M %p')
                sunset = sunset_local.strftime('%I:%M %p')

                emoji = icon_dict.get(icon, None)

                weather_dict = {'emoji': emoji, 'temp': round(curr_temp), 'feels_like': round(feels_like), 'pressure': pressure,
                                'humidity': humidity, 'visibility': visibility, 'speed': wind_speed, 'sunrise': sunrise, 'sunset': sunset}

                return weather_dict

        except requests.exceptions.ConnectionError as e:
            logging.error(f'ConnectionError for {city} city as {e}')
            flash('Something went wrong. Try again later!')

        except Exception as e:
            logging.error(f'Error for {city} city as {e}')
            flash('Something went wrong. Try again later!')


    def get_forecast(self, city):
        lat, lon = self.get_coords(city)

        response = requests.get(f'http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&appid={API_KEY}')
        data = response.json()

        df = pd.json_normalize(data['list'])

        df['temperature'] = df['main.temp']
        df['temperature'] = df['temperature'].round(0)
        df['humidity'] = df['main.humidity']
        df['description'] = df['weather'].apply(lambda x: x[0]['description'])
        df['icon'] = df['weather'].apply(lambda x: x[0]['icon'])
        df['probability'] = df['pop'].apply(lambda x: round(x * 100))
        df['precipitation'] = df['rain.3h']
        df['precipitation'] = df['precipitation'].fillna(0)
        df['datetime'] = df['dt_txt']

        df['datetime'] = pd.to_datetime(df['datetime'])
        df['date_str'] = df['datetime'].dt.strftime('%#d %B')
        df['time'] = df['datetime'].dt.strftime('%H:%M')
        df['date'] = df['datetime'].dt.date

        columns = ['date', 'time', 'date_str', 'temperature', 'probability', 'precipitation', 'humidity', 'description', 'icon']
        df = df[columns]

        avg_temp_df = df.groupby('date')['temperature'].mean().reset_index()
        avg_preci_df = df.groupby('date')['precipitation'].sum().reset_index()
        avg_temp_df['temperature'] = avg_temp_df['temperature'].round(2)
        avg_temp_df['dt_display'] = df['date_str']

        date_str_map = df[['date', 'date_str']].drop_duplicates()

        avg_temp_df = avg_temp_df.merge(date_str_map, on='date', how='left')
        avg_preci_df = avg_preci_df.merge(date_str_map, on='date', how='left')

        avg_temp_df = avg_temp_df.sort_values('date').reset_index(drop=True)
        avg_preci_df = avg_preci_df.sort_values('date').reset_index(drop=True)

        icons = [icon_dict.get(icon) for icon in df['icon'].tolist()[:6] if icon in icon_dict]

        hourly_forecast_df = pd.DataFrame({
            'temp': [round(temp) for temp in df['temperature'].tolist()[:6]],
            'icon': icons,
            'probability': df['probability'].to_list()[:6],
            'description': df['description'].tolist()[:6],
            'time': df['time'].tolist()[:6]
        })

        hourly_forecast_data = hourly_forecast_df.to_dict(orient='records')

        return df, avg_temp_df, avg_preci_df, hourly_forecast_data


    @staticmethod
    def create_charts(forecast_data, avg_temp_df, avg_preci_df):
        linechart = px.line(avg_temp_df, x='date', y='temperature', hover_name='date_str')
        linechart.update_layout(xaxis_title='day', yaxis_title='celsius', height=400, width=300,
                                margin=dict(t=20, r=5, b=20, l=5), xaxis=dict(tickvals=avg_temp_df['date'],
                                                                    ticktext=avg_temp_df['date_str']))

        pie_data = forecast_data['description'].value_counts().reset_index()
        pie_data.columns = ['description', 'count']

        piechart = px.pie(pie_data, values='count', names='description', hole=0.4, hover_name='description',
                          color='description', color_discrete_sequence=['#725CAD', '#FEC5F6', '#FFE99A', '#A4CCD9', '#5459AC', '#FFDCDC'])
        piechart.update_layout(showlegend=False, margin=dict(t=20, r=0, b=40, l=0), height=200, width=300)
        piechart.update_traces(textinfo='none', marker=dict(line=dict(color='#EEEEEE', width=1)))

        scatterchart = px.scatter(avg_preci_df, x='date', y='precipitation', color='date', size_max=60)
        scatterchart.update_layout(showlegend=False, margin=dict(t=20, r=20, b=20, l=40), height=280, width=620,
                                   xaxis=dict(tickvals=avg_preci_df['date'],
                                              ticktext=avg_preci_df['date_str']), hovermode='x unified')

        linechartJSON = linechart.to_json()
        piechartJSON = piechart.to_json()
        scatterchartJSON = scatterchart.to_json()

        return linechartJSON, piechartJSON, scatterchartJSON

