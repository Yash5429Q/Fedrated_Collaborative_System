import { apiClient } from '@/lib/apiClient'
import type { ApiThreatsResponse } from '@/types/api'
import type { ThreatDetectionDetail, ThreatPageSummary, ThreatTimelinePoint, ThreatTypeCount } from '@/types/threats'

export interface ThreatFilters {
  organization?: string
  threatType?:   string
  severity?:     string
  status?:       string
  search?:       string
  page?:         number
  pageSize?:     number
}

export interface ThreatsData {
  summary:      ThreatPageSummary
  detections:   ThreatDetectionDetail[]
  distribution: ThreatTypeCount[]
  timeline:     ThreatTimelinePoint[]
  total:        number
}

export const threatService = {
  async getThreats(filters: ThreatFilters = {}): Promise<ThreatsData> {
    const params = new URLSearchParams()
    if (filters.organization) params.set('organization', filters.organization)
    if (filters.threatType)   params.set('threatType',   filters.threatType)
    if (filters.severity)     params.set('severity',     filters.severity)
    if (filters.status)       params.set('status',       filters.status)
    if (filters.search)       params.set('search',       filters.search)
    if (filters.page)         params.set('page',         String(filters.page))
    if (filters.pageSize)     params.set('pageSize',     String(filters.pageSize))

    const qs = params.toString()
    const r = await apiClient.get<ApiThreatsResponse>(`/threats${qs ? `?${qs}` : ''}`)

    return {
      summary: {
        total:          r.summary.total,
        critical:       r.summary.critical,
        high:           r.summary.high,
        medium:         r.summary.medium,
        low:            r.summary.low,
        blocked:        r.summary.blocked,
        investigating:  r.summary.investigating,
        avgConfidence:  r.summary.avg_confidence,
      },
      detections: r.detections.map(d => ({
        id:              d.id,
        timestamp:       d.timestamp,
        organization:    d.organization,
        organizationId:  d.organization_id,
        threatType:      d.threat_type,
        severity:        d.severity as ThreatDetectionDetail['severity'],
        confidence:      d.confidence,
        status:          d.status as ThreatDetectionDetail['status'],
        modelVersion:    d.model_version,
        sourceIP:        d.source_ip,
        destinationIP:   d.destination_ip,
        protocol:        d.protocol,
        port:            d.port,
        description:     d.description,
        rawFeatures:     d.raw_features,
        detectionMethod: d.detection_method as ThreatDetectionDetail['detectionMethod'],
      })),
      distribution: r.distribution.map(d => ({
        type:  d.type,
        count: d.count,
        color: d.color,
      })),
      timeline: r.timeline.map(t => ({
        hour:     t.hour,
        critical: t.critical,
        high:     t.high,
        medium:   t.medium,
        low:      t.low,
      })),
      total: r.total,
    }
  },
}
