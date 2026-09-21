# NetWeather Roadmap

Roadmap отражает текущую продуктовую концепцию: сперва полезный инструмент и единый probe-контур, затем аккаунты и коммерческое разделение возможностей.

## 0.3.x — Web foundation

### Готово

- [x] Web dashboard
- [x] Global VPS probe
- [x] группы ресурсов
- [x] каталог популярных ресурсов
- [x] дедупликация каталога / ручного ввода
- [x] инциденты и история
- [x] DNS/TCP/TLS/HTTP stages
- [x] server-side traceroute
- [x] configurable Overview
- [x] capability-aware panels
- [x] hardened VPS container
- [x] forced-command deployment channel
- [x] CI security contract

### Сейчас

- [x] единый interaction contract для кнопок, форм и dialog
- [x] минимальная типографика и spacing основных экранов
- [x] состояния loading / empty / error / disabled для основных потоков
- [x] keyboard navigation и базовая accessibility
- [x] полировка resource/groups flows
- [x] успешный end-to-end production auto-deploy
- [x] публичное чтение + защищённая owner-session для изменений
- [x] problem-first Overview с читаемыми KPI, карточками и ограниченной таблицей
- [x] исправление обрезания раскрытых групп каталога
- [x] публикация installable Android alpha-preview APK с SHA-256
- [ ] расширенная матрица device-level QA на физических устройствах

## 0.4 — Probe convergence

- [ ] Keenetic → постоянный `DOMESTIC` probe
- [x] проверяемый Keenetic installer + Entware supervisor
- [x] принудительная привязка DOMESTIC-измерений к прямому WAN `eth2.4`
- [ ] стабильный heartbeat физического probe
- [x] agent version handshake и отображение версии
- [ ] traceroute от domestic probe
- [ ] нормализация результатов всех probes
- [ ] health/status UI для каждой точки наблюдения

## 0.5 — Browser Probe

- [ ] временный browser probe при открытии сайта
- [ ] baseline браузер → NetWeather
- [ ] reachability выбранных ресурсов из пользовательской сети
- [ ] IPv4/IPv6 и network-change awareness
- [ ] сравнение `GLOBAL ↔ DOMESTIC ↔ BROWSER`
- [ ] privacy-first session model

## 0.6 — Fault Domain

- [ ] движок классификации отказа
- [ ] ресурс / CDN / transit / ISP / LAN / device
- [ ] объяснимый вывод вместо сырых кодов ошибок
- [ ] confidence / evidence model
- [ ] маршрут и момент возникновения проблемы

## 0.7 — Alerts & reports

- [ ] настраиваемые триггеры
- [ ] Telegram / webhook
- [ ] отчёты по доступности
- [ ] сравнение периодов
- [ ] экспорт

## 0.8 — Account & capability model

Только после стабилизации основной диагностики.

- [ ] accounts
- [ ] owner/team model
- [ ] capability registry
- [ ] FREE / PERSONAL / BUSINESS как конфигурации capabilities
- [ ] скрытие недоступных панелей без dead UI
- [ ] лицензирование Router / Native / Multi-Probe

## 1.0 — Stable NetWeather

Критерии:

- воспроизводимый deployment;
- web + probes работают как единый продукт;
- понятный fault-domain;
- отсутствие dead controls;
- documented API;
- security baseline;
- backup/restore;
- regression test suite;
- стабильный UX на desktop и mobile.
