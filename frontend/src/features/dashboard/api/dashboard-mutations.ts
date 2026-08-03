import { useMutation, useQueryClient } from '@tanstack/react-query'

import {
  approveScheduledAction,
  pauseScheduledAction,
  rejectScheduledAction,
  resumeScheduledAction,
  retryIntervention,
} from './dashboard-api'
import { dashboardQueryKeys } from './dashboard-query-keys'

export function usePauseScheduledActionMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (variables: Parameters<typeof pauseScheduledAction>[0]) =>
      pauseScheduledAction(variables),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.operationLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.summary() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.incidentLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.interventionLists() }),
      ]),
    retry: false,
  })
}

export function useResumeScheduledActionMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (variables: Parameters<typeof resumeScheduledAction>[0]) =>
      resumeScheduledAction(variables),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.operationLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.summary() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.incidentLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.interventionLists() }),
      ]),
    retry: false,
  })
}

export function useApproveScheduledActionMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (variables: Parameters<typeof approveScheduledAction>[0]) =>
      approveScheduledAction(variables),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.operationLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.summary() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.incidentLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.interventionLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.approvalLists() }),
      ]),
    retry: false,
  })
}

export function useRejectScheduledActionMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (variables: Parameters<typeof rejectScheduledAction>[0]) =>
      rejectScheduledAction(variables),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.operationLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.summary() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.incidentLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.interventionLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.approvalLists() }),
      ]),
    retry: false,
  })
}

export function useRetryInterventionMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (variables: Parameters<typeof retryIntervention>[0]) =>
      retryIntervention(variables),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.interventionLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.operationLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.incidentLists() }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.summary() }),
      ]),
    retry: false,
  })
}
