import { apiClient } from '@/lib/apiClient'
import type { ApiPrivacyResponse } from '@/types/api'
import type { PrivacyPageSummary, PrivacyProperty, OrgUpdateStatus, SecurityEvent } from '@/types/privacy'

export interface PrivacyData {
  summary:           PrivacyPageSummary
  properties:        PrivacyProperty[]
  orgUpdateStatuses: OrgUpdateStatus[]
  securityEvents:    SecurityEvent[]
}

export const privacyService = {
  async getPrivacy(): Promise<PrivacyData> {
    const r = await apiClient.get<ApiPrivacyResponse>('/privacy')
    return {
      summary: {
        rawDataShared:                  r.summary.raw_data_shared,
        modelUpdatesOnly:               r.summary.model_updates_only,
        privacyMechanismsImplemented:   r.summary.privacy_mechanisms_implemented,
        privacyMechanismsPlanned:       r.summary.privacy_mechanisms_planned,
        securityEventsLast24h:          r.summary.security_events_last_24h,
        unauthorizedAttemptsBlocked:    r.summary.unauthorized_attempts_blocked,
      },
      properties: r.properties.map(p => ({
        id:          p.id,
        label:       p.label,
        category:    p.category as PrivacyProperty['category'],
        description: p.description,
        status:      p.status as PrivacyProperty['status'],
        detail:      p.detail,
        planned:     p.planned,
      })),
      orgUpdateStatuses: r.org_update_statuses.map(o => ({
        orgId:            o.org_id,
        orgName:          o.org_name,
        round:            o.round,
        updateStatus:     o.update_status as OrgUpdateStatus['updateStatus'],
        updateSize:       o.update_size ?? null,
        submittedAt:      o.submitted_at ?? null,
        validationPassed: o.validation_passed ?? null,
        notes:            o.notes,
      })),
      securityEvents: r.security_events.map(e => ({
        id:           e.id,
        timestamp:    e.timestamp,
        organization: e.organization ?? null,
        event:        e.event,
        category:     e.category,
        severity:     e.severity as SecurityEvent['severity'],
        status:       e.status as SecurityEvent['status'],
        detail:       e.detail,
      })),
    }
  },
}
