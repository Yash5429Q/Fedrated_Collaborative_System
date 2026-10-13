import { useApiQuery } from './useApiQuery'
import { trainingService } from '@/services/trainingService'
export const useTraining = () => useApiQuery(() => trainingService.getTraining())
