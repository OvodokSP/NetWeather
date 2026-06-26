package io.netweather.app.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import io.netweather.app.R
import io.netweather.app.data.StateStore

class SmallWidgetProvider : BaseWidgetProvider(R.layout.widget_small)
class MediumWidgetProvider : BaseWidgetProvider(R.layout.widget_medium)
class LargeWidgetProvider : BaseWidgetProvider(R.layout.widget_large)
open class BaseWidgetProvider(private val layout: Int) : AppWidgetProvider() {
    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        val summary = StateStore(context).load()
        appWidgetIds.forEach { WidgetUpdater.update(context, appWidgetManager, it, layout, summary) }
    }
}
