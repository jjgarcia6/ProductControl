import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import App from '@/App'

test('App renderiza el heading principal', async () => {
  render(<App />)
  expect(
    await screen.findByRole('heading', { name: 'Sistema de gestión operativa' }),
  ).toBeInTheDocument()
})
