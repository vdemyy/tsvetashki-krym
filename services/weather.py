# Получение погоды через OpenWeather API

import os
import httpx

OW_KEY = os.getenv("OPENWEATHER_API_KEY", "")


class WeatherHint:
    """Подсказка о погоде"""
    def __init__(self, message, raw_summary=None):
        self.message = message
        self.raw_summary = raw_summary


class WeatherDetails:
    """Детали погоды"""
    def __init__(self):
        self.temp_c = None
        self.feels_like_c = None
        self.humidity = None
        self.wind_speed_ms = None
        self.weather_main = None
        self.weather_desc_ru = None
        self.pressure_hpa = None
        self.visibility_km = None


async def rain_hint(lat, lon, hours_ahead=12):
    """Проверяет будут ли осадки в ближайшие часы"""
    if not OW_KEY:
        return WeatherHint(None)
    
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OW_KEY,
        "units": "metric",
        "lang": "ru"
    }
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except:
        return WeatherHint("Погода временно недоступна.")
    
    items = data.get("list", [])
    rainy = []
    
    # Проверяем прогноз на ближайшие часы
    for item in items[:max(1, hours_ahead // 3)]:
        weather = item.get("weather", [{}])[0]
        rain = item.get("rain", {}).get("3h", 0) or 0
        
        # Если дождь или гроза
        if weather.get("main") in ("Rain", "Drizzle", "Thunderstorm") or rain > 0:
            rainy.append(item.get("dt_txt", ""))
    
    if not rainy:
        return WeatherHint(None, "без существенных осадков в ближайшие часы")
    
    return WeatherHint(
        "Возможны осадки в этом районе в ближайшие часы — проверьте прогноз перед выездом.",
        ", ".join(rainy[:3])
    )


async def get_weather_details(lat, lon):
    """Получает текущую погоду для точки"""
    if not OW_KEY:
        return None
    
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OW_KEY,
        "units": "metric",
        "lang": "ru"
    }
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except:
        return None
    
    main = data.get("main", {})
    wind = data.get("wind", {})
    weather = data.get("weather", [{}])[0]
    visibility = data.get("visibility", 0)
    
    details = WeatherDetails()
    details.temp_c = main.get("temp")
    details.feels_like_c = main.get("feels_like")
    details.humidity = main.get("humidity")
    details.wind_speed_ms = wind.get("speed")
    details.weather_main = weather.get("main")
    details.weather_desc_ru = weather.get("description")
    details.pressure_hpa = main.get("pressure")
    details.visibility_km = visibility / 1000.0 if visibility else None
    
    return details
