import { createBrowserRouter } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import DashboardPage from '@/pages/DashboardPage'
import OrganizationsPage from '@/pages/OrganizationsPage'
import TrainingPage from '@/pages/TrainingPage'
import ThreatsPage from '@/pages/ThreatsPage'
import PerformancePage from '@/pages/PerformancePage'
import PrivacyPage from '@/pages/PrivacyPage'
import TestingPage from '@/pages/TestingPage'
import PredictPage from '@/pages/PredictPage'

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'organizations', element: <OrganizationsPage /> },
      { path: 'training', element: <TrainingPage /> },
      { path: 'threats', element: <ThreatsPage /> },
      { path: 'performance', element: <PerformancePage /> },
      { path: 'privacy', element: <PrivacyPage /> },
      { path: 'testing', element: <TestingPage /> },
      { path: 'predict', element: <PredictPage /> },
    ],
  },
])
