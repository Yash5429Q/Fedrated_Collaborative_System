import { useApiQuery } from './useApiQuery'
import { threatService } from '@/services/threatService'
import type { ThreatFilters } from '@/services/threatService'

export const useThreats = (filters: ThreatFilters = {}) =>
  useApiQuery(
    () => threatService.getThreats(filters),
    // Re-fetch when any filter changes
    [
      filters.organization,
      filters.threatType,
      filters.severity,
      filters.status,
      filters.search,
      filters.page,
      filters.pageSize,
    ],
  )
