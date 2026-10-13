import type { ReactNode } from 'react'

export interface Column<T> {
  key: string
  header: string
  render: (row: T) => ReactNode
  align?: 'left' | 'center' | 'right'
  className?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  rowKey: (row: T) => string
  compact?: boolean
}

export default function DataTable<T>({
  columns,
  data,
  rowKey,
  compact = false,
}: DataTableProps<T>) {
  const cellPadding = compact ? 'px-3 py-2' : 'px-4 py-3'

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-cyber-700/50 bg-cyber-800/40">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`${cellPadding} text-left text-xs font-semibold uppercase tracking-wider text-gray-500 ${
                  col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : ''
                } ${col.className ?? ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-cyber-700/30">
          {data.map((row) => (
            <tr key={rowKey(row)} className="transition-colors hover:bg-cyber-800/25">
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`${cellPadding} text-sm ${
                    col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : ''
                  } ${col.className ?? ''}`}
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
