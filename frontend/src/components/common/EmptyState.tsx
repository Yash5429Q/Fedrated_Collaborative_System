import { Inbox } from 'lucide-react'

interface Props {
  message?: string
  detail?:  string
}

/** Shown when an API call returns empty/null data. */
export default function EmptyState({
  message = 'No data available',
  detail,
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-gray-500">
      <Inbox className="h-8 w-8" />
      <p className="text-sm font-medium">{message}</p>
      {detail && <p className="text-xs text-gray-600">{detail}</p>}
    </div>
  )
}
