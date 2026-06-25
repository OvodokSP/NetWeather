package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.widget.RemoteViews
import com.netweather.R
import com.netweather.domain.model.NetworkState
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Провайдер для среднего виджета (4x2)
 * Показывает: Индекс, режим сети и время последней проверки
 */
class MediumWidgetProvider : AppWidgetProvider() {
    
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        WidgetUpdateWorker.enqueueUpdate(context)
    }
    
    override fun onEnabled(context: Context) {
        super.onEnabled(context)
        WidgetUpdateWorker.enqueuePeriodicUpdate(context)
    }
    
    override fun onDisabled(context: Context) {
        super.onDisabled(context)
        WidgetUpdateWorker.cancelPeriodicUpdate(context)
    }
    
    companion object {
        fun updateAppWidget(
            context: Context,
            appWidgetManager: AppWidgetManager,
            appWidgetId: Int,
            networkState: NetworkState?
        ) {
            val views = RemoteViews(context.packageName, R.layout.widget_medium)
            
            if (networkState != null) {
                views.setTextViewText(
                    R.id.tv_availability_index,
                    "${networkState.availabilityIndex.value}%"
                )
                
                views.setTextViewText(
                    R.id.tv_network_mode_emoji,
                    networkState.networkMode.getEmoji()
                )
                views.setTextViewText(
                    R.id.tv_network_mode,
                    networkState.networkMode.getShortDescription()
                )
                
                val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
                val timeString = timeFormat.format(Date(networkState.lastCheckTime))
                views.setTextViewText(
                    R.id.tv_last_check_time,
                    "Обновлено: $timeString"
                )
                
                val indexColor = WidgetUtils.getIndexColor(networkState.availabilityIndex.value)
                views.setTextColor(R.id.tv_availability_index, indexColor)
            } else {
                views.setTextViewText(R.id.tv_availability_index, "--%")
                views.setTextViewText(R.id.tv_network_mode_emoji, "⚪")
                views.setTextViewText(R.id.tv_network_mode, "Нет данных")
                views.setTextViewText(R.id.tv_last_check_time, "Обновлено: --:--")
            }
            
            appWidgetManager.updateAppWidget(appWidgetId, views)
        }
    }
}