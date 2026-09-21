package io.netweather.app.data.network

import android.os.Build
import io.netweather.app.BuildConfig
import io.netweather.app.data.StateStore
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
    private val stateStore: StateStore? = null,
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

    suspend fun startPairing(): DevicePairingState = withContext(Dispatchers.IO) {
        val store = requireNotNull(stateStore) { "StateStore is required for device pairing" }
        val payload = buildJsonObject {
            put("device_id", store.deviceId())
            put("device_name", "${Build.MANUFACTURER} ${Build.MODEL}".trim())
            put("app_version", BuildConfig.VERSION_NAME)
        }.toString().toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder().url("${baseUrl.trimEnd('/')}/api/v1/device-auth/start").post(payload).build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Не удалось получить код: HTTP ${response.code}")
            val root = json.parseToJsonElement(response.body?.string().orEmpty()).jsonObject
            DevicePairingState(
                status = "pending", userCode = root.string("user_code"),
                expiresAtSeconds = root.long("expires_at"), sessionId = root.string("session_id"),
                pollSecret = root.string("poll_secret"), deviceId = store.deviceId(),
            ).also(store::savePairing)
        }
    }

    suspend fun pollPairing(state: DevicePairingState): DevicePairingState = withContext(Dispatchers.IO) {
        val store = requireNotNull(stateStore) { "StateStore is required for device pairing" }
        val payload = buildJsonObject {
            put("session_id", requireNotNull(state.sessionId))
            put("poll_secret", requireNotNull(state.pollSecret))
        }.toString().toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder().url("${baseUrl.trimEnd('/')}/api/v1/device-auth/poll").post(payload).build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Проверка кода: HTTP ${response.code}")
            val root = json.parseToJsonElement(response.body?.string().orEmpty()).jsonObject
            val status = root.string("status", "pending")
            val token = root.string("access_token").takeIf { it.isNotBlank() }
            token?.let(store::saveAccessToken)
            state.copy(status = status, pollSecret = if (token != null) null else state.pollSecret)
                .also(store::savePairing)
        }
    }

    suspend fun uploadResult(result: CheckResult) = withContext(Dispatchers.IO) {
        val store = requireNotNull(stateStore) { "StateStore is required for probe upload" }
        val token = store.accessToken() ?: return@withContext
        val payload = buildJsonObject {
            putJsonObject("payload") {
                put("resource_id", result.resourceId)
                put("status", result.status.name)
                put("response_time_ms", result.responseTimeMs)
                put("message", result.message)
            }
            putJsonObject("probe") {
                put("probe_key", store.deviceId())
                put("name", "${Build.MANUFACTURER} ${Build.MODEL}".trim())
                put("app_version", BuildConfig.VERSION_NAME)
            }
        }.toString().toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder()
            .url("${baseUrl.trimEnd('/')}/api/v1/client-probe/result")
            .header("Authorization", "Bearer $token")
            .post(payload).build()
        client.newCall(request).execute().use { response ->
            if (response.code == 401) {
                store.clearAccessToken()
                error("Привязка устройства истекла. Подключите устройство повторно.")
            }
            if (!response.isSuccessful) error("Передача локального результата: HTTP ${response.code}")
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
