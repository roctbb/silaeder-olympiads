import { describe, expect, it } from 'vitest'
import router from './router'

describe('ленивая загрузка маршрутов', () => {
  it('загружает карточку олимпиады без ошибки ESM-экспортов', async () => {
    const detailRoute = router.getRoutes().find((route) => route.name === 'olympiad')

    expect(detailRoute).toBeDefined()
    await expect(detailRoute.components.default()).resolves.toMatchObject({
      default: expect.any(Object),
    })
  })
})
