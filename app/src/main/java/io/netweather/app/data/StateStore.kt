package io.netweather.app.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import io.netweather.app.domain.model.NetworkMode
import io.netweather.app.domain.model.NetworkSummary
import io.netweather.app.domain.model.DevicePairingState
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import java.util.UUID

class StateStore(context: Context) {
    companion object { const val DEFAULT_INTERVAL_SECONDS = 300 }
    private val prefs = context.getSharedPreferences("netweather_state", Context.MODE_PRIVATE)
    private val keyAlias = "netweather.device.credentials.v1"
    fun save(summary: NetworkSummary) {
        prefs.edit()
            .putInt("index", summary.availabilityIndex)
            .putString("mode", summary.mode.name)
            .putLong("lastUpdated", summary.lastUpdated)
            .putInt("total", summary.total)
            .putInt("available", summary.available)
            .putInt("problematic", summary.problematic)
            .putString("problems", summary.problemNames.joinToString("\n"))
            .apply()
    }
    fun load(): NetworkSummary? {
        val last = prefs.getLong("lastUpdated", 0L)
        if (last == 0L) return null
        val mode = runCatching { NetworkMode.valueOf(prefs.getString("mode", NetworkMode.NO_INTERNET.name)!!) }.getOrDefault(NetworkMode.NO_INTERNET)
        return NetworkSummary(prefs.getInt("index", 0), mode, last, prefs.getInt("total",0), prefs.getInt("available",0), prefs.getInt("problematic",0), prefs.getString("problems", "")!!.lines().filter { it.isNotBlank() })
    }
    fun saveIntervalSeconds(seconds: Int) {
        prefs.edit().putInt("checkIntervalSeconds", seconds.coerceIn(30, 86400)).apply()
    }
    fun loadIntervalSeconds(): Int = prefs.getInt("checkIntervalSeconds", DEFAULT_INTERVAL_SECONDS).coerceIn(30, 86400)
    fun deviceId(): String {
        val current = prefs.getString("deviceId", null)
        if (!current.isNullOrBlank()) return current
        val created = "android-${UUID.randomUUID()}"
        prefs.edit().putString("deviceId", created).apply()
        return created
    }
    fun accessToken(): String? = readSecret("deviceAccessToken")
    fun saveAccessToken(token: String) = writeSecret("deviceAccessToken", token)
    fun clearAccessToken() = prefs.edit().remove("deviceAccessToken").apply()
    fun savePairing(state: DevicePairingState) = prefs.edit()
        .putString("pairingStatus", state.status)
        .putString("pairingCode", state.userCode)
        .putLong("pairingExpires", state.expiresAtSeconds)
        .putString("pairingSession", state.sessionId)
        .apply()
        .also {
            if (state.pollSecret == null) prefs.edit().remove("pairingSecret").apply()
            else writeSecret("pairingSecret", state.pollSecret)
        }
    fun loadPairing(): DevicePairingState = DevicePairingState(
        status = if (accessToken() != null) "authorized" else prefs.getString("pairingStatus", "unpaired") ?: "unpaired",
        userCode = prefs.getString("pairingCode", null),
        expiresAtSeconds = prefs.getLong("pairingExpires", 0),
        sessionId = prefs.getString("pairingSession", null),
        pollSecret = readSecret("pairingSecret"),
        deviceId = deviceId(),
    )

    private fun readSecret(name: String): String? {
        val stored = prefs.getString(name, null)?.takeIf { it.isNotBlank() } ?: return null
        if (!stored.startsWith("enc:v1:")) {
            // Migrate credentials written by earlier preview builds into Android Keystore-backed storage.
            writeSecret(name, stored)
            return stored
        }
        return runCatching {
            val packed = Base64.decode(stored.removePrefix("enc:v1:"), Base64.NO_WRAP)
            val iv = packed.copyOfRange(0, 12)
            val encrypted = packed.copyOfRange(12, packed.size)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, iv))
            String(cipher.doFinal(encrypted), Charsets.UTF_8)
        }.getOrNull()
    }

    private fun writeSecret(name: String, value: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val packed = cipher.iv + cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        prefs.edit().putString(name, "enc:v1:" + Base64.encodeToString(packed, Base64.NO_WRAP)).apply()
    }

    private fun secretKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (keyStore.getKey(keyAlias, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder(keyAlias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build())
            generateKey()
        }
    }
}
