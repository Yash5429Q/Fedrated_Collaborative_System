import { useApiQuery } from './useApiQuery'
import { dashboardService } from '@/services/dashboardService'
export const useDashboard = () => useApiQuery(() => dashboardService.getDashboard())
