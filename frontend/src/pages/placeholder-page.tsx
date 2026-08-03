import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

type PlaceholderPageProps = {
  title: string
}

export function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-medium">{title}</h1>
      <p className="text-muted-foreground">Pantalla temporal.</p>
      <Button variant="outline" asChild>
        <Link to="/">Volver al inicio</Link>
      </Button>
    </main>
  )
}
