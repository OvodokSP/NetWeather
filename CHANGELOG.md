# Changelog

Все значимые изменения NetWeather фиксируются здесь по продуктовым контрольным точкам.

## Unreleased

### UI / UX
- Overview перестроен в операционную иерархию: здоровье → временная картина → выбранные ресурсы → problem-first таблица;
- добавлены KPI доступных ресурсов, типичного отклика и свежести данных;
- таблица Overview ограничена восемью строками, сортирует проблемы первыми и имеет фильтр «Требуют внимания»;
- группы каталога больше не сжимают и не обрезают ресурсы при одновременном раскрытии;
- frontend assets получают общий cache-busting key после UI-изменений.

### Distribution
- добавлена воспроизводимая публикация installable Android alpha-preview APK и SHA-256 в GitHub Releases.

### Probe architecture
- Keenetic Domestic Probe;
- Browser Probe;
- unified fault-domain.

## 0.3.10-web — Interaction contract & GitHub structure

- обновлены README, Roadmap, Security и contributing docs;
- добавлены architecture/UI/status docs и ADR;
- добавлены GitHub issue/PR templates;
- единое поведение dialog: focus, backdrop, Escape, return focus;
- единый busy-state для async actions;
- защита от double-submit;
- собственное подтверждение destructive actions;
- keyboard navigation глобального поиска;
- явное stale-состояние при потере связи с Core;
- фильтр карты регионов теперь реально работает;
- большая карта показывает живые probe points;
- улучшены accessibility labels и focus-visible;
- добавлена поддержка prefers-reduced-motion.

## 0.3.9-web — Isolated production boundary

- NetWeather production container переведён на dedicated UID/GID 10001.
- Read-only root filesystem.
- Drop all Linux capabilities.
- `no-new-privileges`.
- Удалены host bind mounts и Docker socket.
- Добавлена отдельная сеть NetWeather.
- Добавлен nftables egress guard против host/private/VPN access.
- Production image собирается off-host.
- Forced-command deployment key.
- Security contract и hardened runtime smoke в CI.
- Удалён wildcard CORS.
- SPA file serving ограничен frontend root.

## 0.3.8-web — Dashboard preferences

- настраиваемый Overview;
- до 6 закреплённых ресурсов;
- выбор закреплений по группам;
- capability-aware UI;
- панели без данных скрываются;
- минимальный web font-size 10 px.

## 0.3.7-web — Resource catalog

- каталог ресурсов по группам;
- 10 популярных ресурсов на группу;
- batch add;
- duplicate-safe catalog identity;
- ручной target автоматически использует каталоговую сущность при совпадении.

## 0.3.6-web — Reference dashboard parity

- перестроена геометрия Overview;
- единая типографика;
- SVG icon system;
- scrollable resource table;
- availability graph bands;
- incident read/unread improvements.

## 0.1.0-alpha — Android foundation

- Compose UI;
- Room;
- WorkManager;
- widgets;
- local diagnostics.
