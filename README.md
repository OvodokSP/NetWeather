# NetWeather

**The Weather Forecast for Your Internet**

NetWeather — Android-приложение, которое показывает состояние сети. Помогает понять за несколько секунд: работает ли интернет, какие сервисы доступны, а какие нет.

## Что умеет

- Показывает индекс доступности сети от 0 до 100%
- Проверяет ресурсы по цепочке: DNS → TCP → TLS → HTTP
- 4 режима сети: нормально, проблемы, ограничения, нет интернета
- Проверяет российские и международные сайты
- Виджеты для рабочего стола (3 размера)
- История с графиками за час, сутки и неделю
- Уведомления о сбоях и восстановлении
- Красивый дизайн Material 3
- Поддержка светлой и тёмной темы

## Как установить

1. Зайдите в раздел **Releases** справа
2. Скачайте последний APK файл
3. Установите на телефон

## Как собрать самому

Нужны: Android Studio, JDK 17, Android SDK 34

В терминале:
./gradlew assembleDebug

Готовый APK будет в папке app/build/outputs/apk/debug/

## Технологии

Kotlin, Jetpack Compose, Material 3, Hilt, Room, WorkManager, OkHttp

## Лицензия

MIT. Можно использовать свободно.

## Планы на будущее

- Расширенная аналитика
- Сравнение провайдеров
- Прогноз состояния сети
## Maintenance notes

This repository is expected to build through Gradle/GitHub Actions without Python auto-fix scripts. Short monitoring intervals such as 30 seconds are implemented as active one-time WorkManager checks because Android does not support sub-15-minute `PeriodicWorkRequest` intervals.
