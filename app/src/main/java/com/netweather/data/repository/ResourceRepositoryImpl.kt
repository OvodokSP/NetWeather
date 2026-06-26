package com.netweather.data.repository

import com.netweather.data.local.db.dao.ResourceDao
import com.netweather.data.local.db.entity.ResourceEntity
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.repository.ResourceRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ResourceRepositoryImpl @Inject constructor(
    private val resourceDao: ResourceDao
) : ResourceRepository {

    override fun getAllResources(): Flow<List<Resource>> = resourceDao.getAllResources().map { it.map { e -> e.toDomain() } }
    override fun getResourcesByGroup(group: ResourceGroup): Flow<List<Resource>> = resourceDao.getResourcesByGroup(group.name).map { it.map { e -> e.toDomain() } }
    override fun getEnabledResources(): Flow<List<Resource>> = resourceDao.getEnabledResources().map { it.map { e -> e.toDomain() } }
    override suspend fun getResourceById(id: Long): Resource? = resourceDao.getResourceById(id)?.toDomain()
    override suspend fun addResource(resource: Resource): Long = resourceDao.insertResource(ResourceEntity.fromDomain(resource))
    override suspend fun updateResource(resource: Resource) = resourceDao.updateResource(ResourceEntity.fromDomain(resource))
    override suspend fun deleteResource(id: Long) = resourceDao.deleteResourceById(id)
    override suspend fun setResourceEnabled(id: Long, enabled: Boolean) = resourceDao.setResourceEnabled(id, enabled)
    override suspend fun resourceExists(url: String): Boolean = resourceDao.resourceExists(url)
    override suspend fun getResourceCount(group: ResourceGroup): Int = resourceDao.getResourceCount(group.name)
    override suspend fun getTotalResourceCount(): Int = resourceDao.getTotalResourceCount()
    override suspend fun deleteAllResources() = resourceDao.deleteAllResources()
    override suspend fun getAllResourcesOnce(): List<Resource> = resourceDao.getAllResourcesOnce().map { it.toDomain() }

    override suspend fun initializeDefaultResources() {
        if (resourceDao.getTotalResourceCount() > 0) return
        
        val defaults = listOf(
            Resource(name = "Яндекс", url = "https://yandex.ru", group = ResourceGroup.RU),
            Resource(name = "ВКонтакте", url = "https://vk.com", group = ResourceGroup.RU),
            Resource(name = "Госуслуги", url = "https://gosuslugi.ru", group = ResourceGroup.RU),
            Resource(name = "Mail.ru", url = "https://mail.ru", group = ResourceGroup.RU),
            Resource(name = "Rutube", url = "https://rutube.ru", group = ResourceGroup.RU),
            Resource(name = "YouTube", url = "https://youtube.com", group = ResourceGroup.INTL),
            Resource(name = "Reddit", url = "https://reddit.com", group = ResourceGroup.INTL),
            Resource(name = "Instagram", url = "https://instagram.com", group = ResourceGroup.INTL),
            Resource(name = "Telegram", url = "https://telegram.org", group = ResourceGroup.INTL),
            Resource(name = "Discord", url = "https://discord.com", group = ResourceGroup.INTL),
            Resource(name = "GitHub", url = "https://github.com", group = ResourceGroup.INTL),
            Resource(name = "Wikipedia", url = "https://wikipedia.org", group = ResourceGroup.INTL)
        )
        resourceDao.insertResources(defaults.map { ResourceEntity.fromDomain(it) })
    }
}