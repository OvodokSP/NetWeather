package com.netweather.data.local.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.DiagnosticStatus

@Entity(
    tableName = "check_results",
    foreignKeys = [
        ForeignKey(
            entity = ResourceEntity::class,
            parentColumns = ["id"],
            childColumns = ["resource_id"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index(value = ["resource_id"]),
        Index(value = ["timestamp"]),
        Index(value = ["resource_id", "timestamp"])
    ]
)
data class CheckResultEntity(
    @PrimaryKey(autoGenerate = true)
    @ColumnInfo(name = "id")
    val id: Long = 0,
    
    @ColumnInfo(name = "resource_id")
    val resourceId: Long,
    
    @ColumnInfo(name = "timestamp")
    val timestamp: Long = System.currentTimeMillis(),
    
    @ColumnInfo(name = "dns_status")
    val dnsStatus: String,
    
    @ColumnInfo(name = "tcp_status")
    val tcpStatus: String,
    
    @ColumnInfo(name = "tls_status")
    val tlsStatus: String,
    
    @ColumnInfo(name = "http_status")
    val httpStatus: String,
    
    @ColumnInfo(name = "content_status")
    val contentStatus: String,
    
    @ColumnInfo(name = "response_time_ms")
    val responseTimeMs: Long,
    
    @ColumnInfo(name = "error_message")
    val errorMessage: String? = null
) {
    fun toDomain(): CheckResult {
        return CheckResult(
            id = id,
            resourceId = resourceId,
            timestamp = timestamp,
            dnsStatus = DiagnosticStatus.valueOf(dnsStatus),
            tcpStatus = DiagnosticStatus.valueOf(tcpStatus),
            tlsStatus = DiagnosticStatus.valueOf(tlsStatus),
            httpStatus = DiagnosticStatus.valueOf(httpStatus),
            contentStatus = DiagnosticStatus.valueOf(contentStatus),
            responseTimeMs = responseTimeMs,
            errorMessage = errorMessage
        )
    }
    
    companion object {
        fun fromDomain(checkResult: CheckResult): CheckResultEntity {
            return CheckResultEntity(
                id = checkResult.id,
                resourceId = checkResult.resourceId,
                timestamp = checkResult.timestamp,
                dnsStatus = checkResult.dnsStatus.name,
                tcpStatus = checkResult.tcpStatus.name,
                tlsStatus = checkResult.tlsStatus.name,
                httpStatus = checkResult.httpStatus.name,
                contentStatus = checkResult.contentStatus.name,
                responseTimeMs = checkResult.responseTimeMs,
                errorMessage = checkResult.errorMessage
            )
        }
    }
}