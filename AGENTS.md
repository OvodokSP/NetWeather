# NetWeather Agent Rules

1. Do not rewrite the project from scratch unless explicitly requested.
2. Keep Kotlin files under `app/src/main/java` according to their package names.
3. Keep Android resources only under valid `res` folders and never commit `.backup` files.
4. Build through Gradle only. Do not use Python scripts to patch source code during CI.
5. Before merging functional changes, run: `./gradlew clean assembleDebug`.
6. Main screen, widgets and workers must use the same persisted check results.
7. Do not use `PeriodicWorkRequest` for intervals below 15 minutes.
8. Short intervals such as 30 seconds and 1 minute must use one-time WorkManager jobs with re-scheduling.
9. Update README/CHANGELOG when user-visible behavior changes.
