import { useApiQuery } from './useApiQuery'
import { performanceService } from '@/services/performanceService'
export const usePerformance = () => useApiQuery(() => performanceService.getPerformance())
