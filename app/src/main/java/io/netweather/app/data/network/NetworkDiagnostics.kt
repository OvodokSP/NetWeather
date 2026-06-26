package io.netweather.app.data.network

import io.netweather.app.domain.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.util.concurrent.TimeUnit
import javax.net.ssl.HttpsURLConnection
import java.net.URL

class NetworkDiagnostics {
    private val client = OkHttpClient.Builder().connectTimeout(4, TimeUnit.SECONDS).readTimeout(4, TimeUnit.SECONDS).callTimeout(8, TimeUnit.SECONDS).build()

    suspend fun check(resource: MonitoredResource): CheckResult = withContext(Dispatchers.IO) {
        val start = System.currentTimeMillis()
        try {
            val parsed = normalize(resource.url)
            val host = URL(parsed).host
            runCatching { InetAddress.getByName(host) }.getOrElse { return@withContext result(resource, DiagnosticStatus.DNS_ERROR, start, it.message ?: "DNS error") }
            val port = if (parsed.startsWith("https://")) 443 else 80
            runCatching { Socket().use { it.connect(InetSocketAddress(host, port), 3500) } }.getOrElse { return@withContext result(resource, DiagnosticStatus.TCP_ERROR, start, it.message ?: "TCP error") }
            if (parsed.startsWith("https://")) {
                runCatching { (URL(parsed).openConnection() as HttpsURLConnection).apply { connectTimeout = 3500; readTimeout = 3500; requestMethod = "HEAD"; connect(); responseCode; disconnect() } }.getOrElse { return@withContext result(resource, DiagnosticStatus.TLS_ERROR, start, it.message ?: "TLS error") }
            }
            val method = when(resource.method) { CheckMethod.HTTP_HEAD, CheckMethod.HTTPS_HEAD -> "HEAD"; CheckMethod.DNS -> return@withContext result(resource, DiagnosticStatus.OK, start, "DNS OK"); CheckMethod.TCP -> return@withContext result(resource, DiagnosticStatus.OK, start, "TCP OK"); else -> "GET" }
            val request = Request.Builder().url(parsed).method(method, null).build()
            client.newCall(request).execute().use { resp ->
                if (resp.code in 200..399) result(resource, DiagnosticStatus.OK, start, "HTTP ${resp.code}") else result(resource, DiagnosticStatus.HTTP_ERROR, start, "HTTP ${resp.code}")
            }
        } catch (e: java.net.SocketTimeoutException) { result(resource, DiagnosticStatus.TIMEOUT, start, "Timeout")
        } catch (e: Exception) { result(resource, DiagnosticStatus.UNKNOWN_ERROR, start, e.message ?: "Unknown") }
    }

    private fun result(r: MonitoredResource, status: DiagnosticStatus, start: Long, message: String) = CheckResult(r.id, status, System.currentTimeMillis() - start, message = message, lastSuccessfulCheck = if (status == DiagnosticStatus.OK) System.currentTimeMillis() else null)
    private fun normalize(url: String): String = if (url.startsWith("http://") || url.startsWith("https://")) url else "https://$url"
}
