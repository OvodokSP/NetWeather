package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.graphics.Color
import com.netweather.domain.model.NetworkState
import com.netweather.domain.model.ResourceGroup

/**
 * Утилиты для работы с виджетами
 */
object WidgetUtils {
    
    /**
     * Получение цвета для индекса доступности (возвращает Android Color Int)
     */
    fun getIndexColor(index: Int): Int {
        return when {
            index >= 80 -> Color.parseColor("#2ECC71") // Зелёный
            index >= 70 -> Color.parseColor("#F1C40F") // Жёлтый
            index >= 30 -> Color.parseColor("#E67E22") // Оранжевый
            else -> Color.parseColor("#E74C3C")        // Красный
        }
    }
    
    /**
     * Получение списка проблемных сервисов в виде текста
     */
    fun getProblemServicesText(networkState: NetworkState): String {
        val problemServices = mutableListOf<String>()
        
        networkState.resourceStates.forEach { (_, resources) ->
            resources.filter { !it.isAvailable }.forEach { resourceState ->
                problemServices.add("• ${resourceState.resource.name}")
            }
        }
        
        return if (problemServices.isEmpty()) {
            "✅ Все сервисы работают нормально"
        } else {
            problemServices.joinToString("\n")
        }
    }
    
    /**
     * Обновление всех активных виджетов приложения
     */
    fun updateAllWidgets(context: Context, networkState: NetworkState?) {
        val appWidgetManager = AppWidgetManager.getInstance(context)
        
        // Обновление малых виджетов
        val smallWidgetIds = appWidgetManager.getAppWidgetIds(
            ComponentName(context, SmallWidgetProvider::class.java)
        )
        smallWidgetIds.forEach { widgetId ->
            SmallWidgetProvider.updateAppWidget(context, appWidgetManager, widgetId, networkState)
        }
        
        // Обновление средних виджетов
        val mediumWidgetIds = appWidgetManager.getAppWidgetIds(
            ComponentName(context, MediumWidgetProvider::class.java)
        )
        mediumWidgetIds.forEach { widgetId ->
            MediumWidgetProvider.updateAppWidget(context, appWidgetManager, widgetId, networkState)
        }
        
        // Обновление больших виджетов
        val largeWidgetIds = appWidgetManager.getAppWidgetIds(
            ComponentName(context, LargeWidgetProvider::class.java)
        )
        largeWidgetIds.forEach { widgetId ->
            LargeWidgetProvider.updateAppWidget(context, appWidgetManager, widgetId, networkState)
        }
    }
}