import { createHash } from 'node:crypto'
import { createRequire } from 'node:module'
import { describe, expect, it } from 'vitest'
import appConfig from '../../tailwind.config.js'

const require = createRequire(import.meta.url)
const typography = require('@tailwindcss/typography')
const merge = require('lodash.merge')

// Baselines captured with typography 0.5.16/parser 6.0.10 and this app's exact
// typography configuration. The parser security override must preserve every
// generated component and variant, including code pseudo-elements.
describe('typography selector compatibility', () => {
  it.each([
    ['modern', {}, '', '742e585817f5d3d789bc6342e198f9104da62c1c748791f32f037e7972212517'],
    ['prefixed', {}, 'fuze-', '69aa7b2e9bd29d277fe237ba7908937d7fc402a3562b2bc9af53eb68d25b8ad6'],
    ['legacy', { target: 'legacy' }, '', '3d0d3bbd03dd28cd05e9e4e65f45566cf7970dc5d231a75215a02d9e1bbe72bf'],
    ['custom-class', { className: 'docs' }, '', '91f20acd833a89bf4b2bf184fe1ebd7ef512d96a9f6368943e39d0c1dd139540'],
  ])('preserves all components and variants for %s', (_name, options, prefixValue, baseline) => {
    const plugin = typography(options)
    const variants = []
    const components = []
    plugin.handler({
      theme: () => merge({}, plugin.config.theme.typography, appConfig.theme.extend.typography),
      prefix: selector => prefixValue ? selector.replace(/^\./, '.' + prefixValue) : selector,
      addVariant: (...args) => variants.push(args),
      addComponents: value => components.push(value),
    })
    expect(variants).toHaveLength(29)
    expect(components[0]).toHaveLength(29)
    expect(createHash('sha256').update(JSON.stringify({ variants, components })).digest('hex')).toBe(baseline)
  })
})

it('compiles prose documentation styles through the actual Tailwind 4 plugin loader', async () => {
  const { compile } = require('tailwindcss')
  const { dirname } = require('node:path')
  const compiler = await compile('@plugin "@tailwindcss/typography"; @tailwind utilities;', {
    loadModule: async id => ({ module: require(id), base: dirname(require.resolve(id)) }),
  })
  const css = compiler.build(['prose', 'prose-gray', 'prose-lg', 'prose-invert'])
  expect(css).toContain('.prose')
  expect(css).toContain('not-prose')
  expect(css).toContain('code')
})
