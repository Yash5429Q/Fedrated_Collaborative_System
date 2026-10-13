import { useApiQuery } from './useApiQuery'
import { testingService } from '@/services/testingService'
export const useTesting = () => useApiQuery(() => testingService.getTesting())
