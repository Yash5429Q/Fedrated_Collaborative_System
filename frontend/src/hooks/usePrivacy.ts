import { useApiQuery } from './useApiQuery'
import { privacyService } from '@/services/privacyService'
export const usePrivacy = () => useApiQuery(() => privacyService.getPrivacy())
