# currency_converter
Простой тестовый проект сервиса конвертера валют USD -> RUB

Источник данных: https://openexchangerates.org/

Запуск из контейнера:
```
bash rebuild_container.sh
```

Пример запроса:
```
curl --request GET \
  --url http://192.168.99.100:8080/convert/99.98 \
  --header 'accept: application/json' \
  --header 'host: currency_converter'

```

Пример ответа в фотмате JSON:
```
{
  "timestamp": 1586141985,
  "base_currency": "USD",
  "base_amount": 99.98,
  "target_currency": "RUB",
  "target_amount": 7710.897512
}
```

