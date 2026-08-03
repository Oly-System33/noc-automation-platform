import type { ComponentProps } from 'react'
import { Link, useInRouterContext } from 'react-router-dom'

type AppLinkProps = Omit<ComponentProps<'a'>, 'href'> & { href: string }

export function AppLink({ href, ...props }: AppLinkProps) {
  const inRouter = useInRouterContext()
  return inRouter ? <Link to={href} {...props} /> : <a href={href} {...props} />
}
