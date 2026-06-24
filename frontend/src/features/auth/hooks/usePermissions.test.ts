import { describe, expect, it } from 'vitest'

import { derivePermissions } from './usePermissions'
import type { ProfileType } from '../types/auth.types'

const profile: ProfileType = {
  id: '11111111-1111-1111-1111-111111111111',
  name: 'Jefe',
  description: '',
  permissions: { 'access-control': ['read', 'create'] },
  visible_sensitive_fields: ['intake.cost'],
  auto_approval: true,
}

describe('derivePermissions', () => {
  it('canDo es true para un permiso que el perfil tiene', () => {
    expect(derivePermissions(profile).canDo('access-control', 'read')).toBe(true)
  })

  it('canDo es false para una acción que el perfil no tiene', () => {
    expect(derivePermissions(profile).canDo('access-control', 'delete')).toBe(false)
  })

  it('canDo es false para un módulo desconocido', () => {
    expect(derivePermissions(profile).canDo('kardex', 'read')).toBe(false)
  })

  it('canSee es true para un campo sensible visible', () => {
    expect(derivePermissions(profile).canSee('intake', 'cost')).toBe(true)
  })

  it('canSee es false para un campo no listado', () => {
    expect(derivePermissions(profile).canSee('intake', 'margin')).toBe(false)
  })

  it('sin perfil, todo gating es false', () => {
    const helpers = derivePermissions(null)
    expect(helpers.canDo('access-control', 'read')).toBe(false)
    expect(helpers.canSee('intake', 'cost')).toBe(false)
    expect(helpers.profile).toBeNull()
  })
})
