import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { env } from '@/config/env'

const routes = [
  ['/incidentes', 'Incidentes'],
  ['/operaciones', 'Operaciones'],
  ['/aprobaciones', 'Aprobaciones'],
] as const

export function HomePage() {
  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle>Frontend NOC listo</CardTitle>
          <CardDescription>
            React, Tailwind CSS y shadcn/ui están configurados.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <p className="text-sm text-muted-foreground">
            Backend configurado: <code>{env.apiBaseUrl}</code>
          </p>
          <nav className="flex flex-wrap gap-2" aria-label="Rutas temporales">
            {routes.map(([path, label]) => (
              <Button key={path} variant="outline" asChild>
                <Link to={path}>{label}</Link>
              </Button>
            ))}
          </nav>
        </CardContent>
      </Card>
    </main>
  )
}
