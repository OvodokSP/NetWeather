package com.netweather.data.remote

import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.DiagnosticStatus
import com.netweather.domain.model.Resource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.InetAddress
import java.net.Socket
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException
import javax.inject.Inject
import javax.inject.Singleton
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocket

@Singleton
class NetworkDiagnostics @Inject constructor(
    private val networkClient: NetworkClient
) {
    companion object {
        private const val DEFAULT_TIMEOUT_MS = 10000L
    }

    suspend fun performFullDiagnostics(
        resource: Resource,
        timeoutMs: Long = DEFAULT_TIMEOUT_MS
    ): CheckResult = withContext(Dispatchers.IO) {
        val startTime = System.currentTimeMillis()
        try {
            val url = URL(resource.url)
            val host = url.host
            val port = if (url.port != -1) url.port else if (url.protocol == "https") 443 else 80
            val isHttps = url.protocol == "https"

            // 1. DNS
            val dnsResult = checkDns(host, timeoutMs)
            if (dnsResult != DiagnosticStatus.OK) {
                return@withContext createResult(resource, startTime, dnsResult, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, "DNS failed")
            }

            // 2. TCP
            val tcpResult = checkTcp(host, port, timeoutMs)
            if (tcpResult != DiagnosticStatus.OK) {
                return@withContext createResult(resource, startTime, dnsResult, tcpResult, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, "TCP failed")
            }

            // 3. TLS
            val tlsResult = if (isHttps) checkTls(host, port, timeoutMs) else DiagnosticStatus.OK
            if (tlsResult != DiagnosticStatus.OK) {
                return@withContext createResult(resource, startTime, dnsResult, tcpResult, tlsResult, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, "TLS failed")
            }

            // 4. HTTP
            val httpResult = checkHttp(resource.url)
            if (httpResult.first != DiagnosticStatus.OK) {
                return@withContext createResult(resource, startTime, dnsResult, tcpResult, tlsResult, httpResult.first, DiagnosticStatus.UNKNOWN_ERROR, httpResult.second)
            }

            // 5. Content
            val contentResult = checkContent(httpResult.second)
            createResult(resource, startTime, dnsResult, tcpResult, tlsResult, httpResult.first, contentResult, if (contentResult != DiagnosticStatus.OK) "Content failed" else null)

        } catch (e: Exception) {
            createResult(resource, startTime, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, e.message)
        }
    }

    suspend fun isAvailable(resource: Resource): Boolean = withContext(Dispatchers.IO) {
        try {
            val response = networkClient.executeHead(resource.url)
            response.use { it.isSuccessful }
        } catch (e: Exception) {
            false
        }
    }

    private fun checkDns(host: String, timeoutMs: Long): DiagnosticStatus {
        return try {
            val thread = Thread { InetAddress.getAllByName(host) }
            thread.start()
            thread.join(timeoutMs)
            if (thread.isAlive) { thread.interrupt(); DiagnosticStatus.TIMEOUT } else DiagnosticStatus.OK
        } catch (e: UnknownHostException) { DiagnosticStatus.DNS_ERROR }
        catch (e: Exception) { DiagnosticStatus.UNKNOWN_ERROR }
    }

    private fun checkTcp(host: String, port: Int, timeoutMs: Long): DiagnosticStatus {
        var socket: Socket? = null
        return try {
            socket = Socket()
            socket.soTimeout = timeoutMs.toInt()
            socket.connect(java.net.InetSocketAddress(host, port), timeoutMs.toInt())
            DiagnosticStatus.OK
        } catch (e: SocketTimeoutException) { DiagnosticStatus.TIMEOUT }
        catch (e: Exception) { DiagnosticStatus.TCP_ERROR }
        finally { try { socket?.close() } catch (_: Exception) {} }
    }

    private fun checkTls(host: String, port: Int, timeoutMs: Long): DiagnosticStatus {
        var socket: SSLSocket? = null
        return try {
            val sslContext = SSLContext.getInstance("TLS")
            sslContext.init(null, null, null)
            socket = sslContext.socketFactory.createSocket(host, port) as SSLSocket
            socket.soTimeout = timeoutMs.toInt()
            socket.startHandshake()
            DiagnosticStatus.OK
        } catch (e: SocketTimeoutException) { DiagnosticStatus.TIMEOUT }
        catch (e: Exception) { DiagnosticStatus.TLS_ERROR }
        finally { try { socket?.close() } catch (_: Exception) {} }
    }

    private fun checkHttp(url: String): Pair<DiagnosticStatus, okhttp3.Response?> {
        return try {
            val response = networkClient.executeGet(url)
            if (response.isSuccessful || response.code in 300..399) {
                Pair(DiagnosticStatus.OK, response)
            } else {
                Pair(DiagnosticStatus.HTTP_ERROR, response)
            }
        } catch (e: Exception) {
            Pair(DiagnosticStatus.HTTP_ERROR, null)
        }
    }

    private fun checkContent(response: okhttp3.Response?): DiagnosticStatus {
        if (response == null || response.body == null) return DiagnosticStatus.CONTENT_ERROR
        return try {
            val body = response.body!!
            if (body.contentLength() > 0 && body.contentLength() < 100) return DiagnosticStatus.CONTENT_ERROR
            val source = body.source()
            source.request(100L)
            if (source.buffer.size < 100) DiagnosticStatus.CONTENT_ERROR else DiagnosticStatus.OK
        } catch (e: Exception) {
            DiagnosticStatus.CONTENT_ERROR
        }
    }

    private fun createResult(
        resource: Resource, startTime: Long,
        dns: DiagnosticStatus, tcp: DiagnosticStatus, tls: DiagnosticStatus,
        http: DiagnosticStatus, content: DiagnosticStatus, error: String?
    ): CheckResult {
        return CheckResult(
            resourceId = resource.id,
            timestamp = System.currentTimeMillis(),
            dnsStatus = dns, tcpStatus = tcp, tlsStatus = tls,
            httpStatus = http, contentStatus = content,
            responseTimeMs = System.currentTimeMillis() - startTime,
            errorMessage = error
        )
    }
}