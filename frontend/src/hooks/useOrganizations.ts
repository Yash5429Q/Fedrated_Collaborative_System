import { useApiQuery } from './useApiQuery'
import { organizationService } from '@/services/organizationService'
export const useOrganizations = () => useApiQuery(() => organizationService.getOrganizations())
