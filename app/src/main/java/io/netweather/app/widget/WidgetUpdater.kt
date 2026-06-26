package io.netweather.app.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import io.netweather.app.MainActivity
import io.netweather.app.R
import io.netweather.app.domain.model.NetworkSummary
import java.text.SimpleDateFormat
import java.util.*

object WidgetUpdater {
    fun updateAll(context: Context, summary: NetworkSummary?) {
        val manager = AppWidgetManager.getInstance(context)
        listOf(SmallWidgetProvider::class.java to R.layout.widget_small, MediumWidgetProvider::class.java to R.layout.widget_medium, LargeWidgetProvider::class.java to R.layout.widget_large).forEach { (clazz, layout) ->
            manager.getAppWidgetIds(ComponentName(context, clazz)).forEach { update(context, manager, it, layout, summary) }
        }
    }
    fun update(context: Context, manager: AppWidgetManager, id: Int, layout: Int, summary: NetworkSummary?) {
        val views = RemoteViews(context.packageName, layout)
        val intent = Intent(context, MainActivity::class.java)
        val pending = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        views.setOnClickPendingIntent(R.id.title, pending)
        if (summary == null) {
            views.setTextViewText(R.id.index, "Нет данных"); views.setTextViewText(R.id.mode, "Откройте приложение"); views.setTextViewText(R.id.counts, ""); views.setTextViewText(R.id.time, "")
        } else {
            views.setTextViewText(R.id.index, "${summary.availabilityIndex}%")
            views.setTextViewText(R.id.mode, "${summary.mode.emoji} ${summary.mode.title}")
            views.setTextViewText(R.id.counts, "OK ${summary.available} / Проблем ${summary.problematic}")
            views.setTextViewText(R.id.time, SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(summary.lastUpdated)))
            if (layout == R.layout.widget_large) views.setTextViewText(R.id.problemList, summary.problemNames.joinToString("\n") { "• $it" }.ifBlank { "✅ Все сервисы работают" })
        }
        manager.updateAppWidget(id, views)
    }
}
