package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.widget.RemoteViews
import com.netweather.R
import com.netweather.domain.model.NetworkState
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

/**
 * Провайдер для малого виджета (2x2)
 * Показывает: Индекс доступности и количество проблемных ресурсов
 */
class SmallWidgetProvider : AppWidgetProvider() {
    
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        // При обновлении виджета запускаем Worker для получения свежих данных
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
            val views = RemoteViews(context.packageName, R.layout.widget_small)
            
            if (networkState != null) {
                views.setTextViewText(
                    R.id.tv_availability_index,
                    "${networkState.availabilityIndex.value}%"
                )
                
                val problemText = if (networkState.unavailableCount > 0) {
                    "${networkState.unavailableCount} проблем"
                } else {
                    "Всё отлично"
                }
                views.setTextViewText(R.id.tv_problem_count, problemText)
                
                val indexColor = WidgetUtils.getIndexColor(networkState.availabilityIndex.value)
                views.setTextColor(R.id.tv_availability_index, indexColor)
            } else {
                views.setTextViewText(R.id.tv_availability_index, "--%")
                views.setTextViewText(R.id.tv_problem_count, "Нет данных")
            }
            
            appWidgetManager.updateAppWidget(appWidgetId, views)
        }
    }
}