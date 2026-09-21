package io.netweather.app.data.network

import io.netweather.app.domain.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.*
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class NetWeatherApi(
    private val baseUrl: String = "https://netweather.online",
) {
    private val json = Json { ignoreUnknownKeys = true }
    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .callTimeout(12, TimeUnit.SECONDS)
        .build()

    suspend fun dashboard(): RemoteDashboard = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("${baseUrl.trimEnd('/')}/api/dashboard").get().build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("NetWeather API: HTTP ${response.code}")
            val root = json.parseToJsonElement(response.body?.string().orEmpty()).jsonObject
            val summary = root["summary"]?.jsonObject ?: buildJsonObject { }
            val resources = (root["resources"]?.jsonArray ?: buildJsonArray { }).map { element ->
                val item = element.jsonObject
                val group = runCatching { ResourceGroup.valueOf(item.string("group_name")) }.getOrDefault(ResourceGroup.CUSTOM)
                RemoteResource(
                    id = item.long("id"),
                    name = item.string("name"),
                    target = item.string("target"),
                    group = group,
                    enabled = item.boolean("enabled", true),
                    intervalSeconds = item.int("interval_seconds", 300),
                )
            }
            RemoteDashboard(
                resources = resources,
                global = GlobalState(
                    availability = summary["availability_index"]?.jsonPrimitive?.intOrNull,
                    mode = summary.string("mode", "NO_DATA"),
                    lastUpdatedSeconds = summary.long("last_updated", 0),
                    active = true,
                ),
            )
        }
    }

    suspend fun addResource(resource: MonitoredResource): Long = withContext(Dispatchers.IO) {
        val payload = buildJsonObject {
            put("name", resource.name)
            put("target", resource.url)
            put("group_name", resource.group.name)
        }.toString().toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder().url("${baseUrl.trimEnd('/')}/api/resources").post(payload).build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Не удалось добавить ресурс: HTTP ${response.code}")
            json.parseToJsonElement(response.body?.string().orEmpty()).jsonObject.long("id")
        }
    }

    private fun JsonObject.string(key: String, fallback: String = ""): String = this[key]?.jsonPrimitive?.contentOrNull ?: fallback
    private fun JsonObject.long(key: String, fallback: Long = 0): Long = this[key]?.jsonPrimitive?.longOrNull ?: fallback
    private fun JsonObject.int(key: String, fallback: Int = 0): Int = this[key]?.jsonPrimitive?.intOrNull ?: fallback
    private fun JsonObject.boolean(key: String, fallback: Boolean = false): Boolean = this[key]?.jsonPrimitive?.booleanOrNull ?: fallback
}

data class RemoteResource(
    val id: Long,
    val name: String,
    val target: String,
    val group: ResourceGroup,
    val enabled: Boolean,
    val intervalSeconds: Int,
)

data class RemoteDashboard(val resources: List<RemoteResource>, val global: GlobalState)
