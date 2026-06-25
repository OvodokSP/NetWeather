#!/usr/bin/env python3
import os

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created: {path}")

# strings.xml
write_file('app/src/main/res/values/strings.xml', '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">NetWeather</string>
    <string name="widget_small_label">NetWeather Small</string>
    <string name="widget_medium_label">NetWeather Medium</string>
    <string name="widget_large_label">NetWeather Large</string>
    <string name="widget_small_description">Availability index</string>
    <string name="widget_medium_description">Index and mode</string>
    <string name="widget_large_description">Full information</string>
</resources>
''')

# themes.xml
write_file('app/src/main/res/values/themes.xml', '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.NetWeather" parent="android:Theme.Material.Light.NoActionBar">
        <item name="android:statusBarColor">@android:color/transparent</item>
    </style>
</resources>
''')

# colors.xml
write_file('app/src/main/res/values/colors.xml', '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="widget_background">#FFFFFFFF</color>
    <color name="widget_background_dark">#FF1F1F1F</color>
    <color name="widget_text_primary">#FF191C1A</color>
    <color name="widget_text_secondary">#FF707973</color>
    <color name="widget_divider">#FFE0E0E0</color>
</resources>
''')

# ic_launcher_background.xml (values)
write_file('app/src/main/res/values/ic_launcher_background.xml', '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#006C4C</color>
</resources>
''')

# data_extraction_rules.xml
write_file('app/src/main/res/xml/data_extraction_rules.xml', '''<?xml version="1.0" encoding="utf-8"?>
<data-extraction-rules>
    <cloud-backup>
        <include domain="sharedpref" path="."/>
    </cloud-backup>
    <device-transfer>
        <include domain="sharedpref" path="."/>
    </device-transfer>
</data-extraction-rules>
''')

# backup_rules.xml
write_file('app/src/main/res/xml/backup_rules.xml', '''<?xml version="1.0" encoding="utf-8"?>
<full-backup-content>
    <include domain="sharedpref" path="."/>
</full-backup-content>
''')

# widget_small_info.xml
write_file('app/src/main/res/xml/widget_small_info.xml', '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="110dp"
    android:minHeight="110dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@layout/widget_small"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''')

# widget_medium_info.xml
write_file('app/src/main/res/xml/widget_medium_info.xml', '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp"
    android:minHeight="110dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@layout/widget_medium"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''')

# widget_large_info.xml
write_file('app/src/main/res/xml/widget_large_info.xml', '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp"
    android:minHeight="250dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@layout/widget_large"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''')

# ic_launcher_foreground.xml
write_file('app/src/main/res/drawable/ic_launcher_foreground.xml', '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M72,58c0,-6.6 -5.4,-12 -12,-12c-0.7,0 -1.4,0.1 -2,0.2C56.6,39.5 50,34 42,34c-8.8,0 -16,7.2 -16,16c0,0.5 0,1 0.1,1.5C22.4,52.6 20,56 20,60c0,5.5 4.5,10 10,10h40C75.5,70 80,65.5 80,60C80,54.5 76.5,50 72,50z"/>
    <path
        android:fillColor="#006C4C"
        android:pathData="M54,50c-3.3,0 -6,2.7 -6,6s2.7,6 6,6s6,-2.7 6,-6S57.3,50 54,50z"/>
</vector>
''')

# ic_launcher_background.xml (drawable)
write_file('app/src/main/res/drawable/ic_launcher_background.xml', '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#006C4C"
        android:pathData="M0,0h108v108h-108z"/>
</vector>
''')

# ic_launcher.xml
write_file('app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml', '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
''')

# ic_launcher_round.xml
write_file('app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml', '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
''')

print("All resources created successfully!")