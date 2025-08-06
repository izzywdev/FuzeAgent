import { type ReactNode } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  change?: {
    value: string
    type: 'increase' | 'decrease' | 'neutral'
  }
  icon: ReactNode
  className?: string
}

export function MetricCard({ title, value, change, icon, className }: MetricCardProps) {
  return (
    <Card className={cn("relative overflow-hidden", className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold text-foreground">{value}</p>
            {change && (
              <div className="flex items-center mt-2">
                <Badge 
                  variant={change.type === 'increase' ? 'default' : change.type === 'decrease' ? 'destructive' : 'secondary'}
                  className="text-xs"
                >
                  {change.value}
                </Badge>
                <span className="text-xs text-muted-foreground ml-2">vs last period</span>
              </div>
            )}
          </div>
          <div className="p-3 rounded-full bg-primary/10">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}