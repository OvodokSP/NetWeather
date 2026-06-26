# NetWeather Agent Rules

1. Do not rewrite the project from scratch unless explicitly requested.
2. Do not use Python scripts to patch Android code during CI.
3. GitHub Actions must build directly through Gradle.
4. Widgets, UI and WorkManager must use the same persisted network state.
5. Do not use PeriodicWorkRequest for intervals below 15 minutes.
6. Every functional change must keep the project buildable.
