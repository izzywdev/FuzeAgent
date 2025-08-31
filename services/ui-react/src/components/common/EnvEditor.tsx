import React, { useMemo } from 'react'

export interface EnvEditorProps {
  value: Record<string, string>
  onChange: (next: Record<string, string>) => void
}

export function EnvEditor({ value, onChange }: EnvEditorProps): JSX.Element {
  const entries = useMemo(() => Object.entries(value || {}), [value])

  const updateEntry = (index: number, key: string, val: string) => {
    const next: Record<string, string> = {}
    entries.forEach(([k, v], i) => {
      const newKey = i === index ? key : k
      const newVal = i === index ? val : v
      if (newKey) next[newKey] = newVal
    })
    if (index === entries.length && key) {
      next[key] = val
    }
    onChange(next)
  }

  const removeEntry = (index: number) => {
    const next: Record<string, string> = {}
    entries.forEach(([k, v], i) => {
      if (i !== index) next[k] = v
    })
    onChange(next)
  }

  const addEmpty = () => {
    const next: Record<string, string> = { ...value }
    let candidate = 'NEW_VAR'
    let suffix = 1
    while (Object.prototype.hasOwnProperty.call(next, candidate)) {
      candidate = `NEW_VAR_${suffix++}`
    }
    next[candidate] = ''
    onChange(next)
  }

  return (
    <div style={{border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '1rem'}}>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '0.5rem'}}>
        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>Key</div>
        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>Value</div>
        <div></div>
        {entries.map(([k, v], i) => (
          <React.Fragment key={i}>
            <input
              type="text"
              value={k}
              onChange={(e) => updateEntry(i, e.target.value, v)}
              placeholder="ENV_KEY"
              style={{padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem'}}
            />
            <input
              type="text"
              value={v}
              onChange={(e) => updateEntry(i, k, e.target.value)}
              placeholder="value"
              style={{padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem'}}
            />
            <button
              type="button"
              onClick={() => removeEntry(i)}
              style={{padding: '0.5rem 0.75rem', border: '1px solid #d1d5db', backgroundColor: 'white', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}
            >
              Remove
            </button>
          </React.Fragment>
        ))}
      </div>
      <div style={{marginTop: '0.75rem'}}>
        <button
          type="button"
          onClick={addEmpty}
          style={{padding: '0.5rem 0.75rem', border: '1px solid #d1d5db', backgroundColor: 'white', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}
        >
          + Add Variable
        </button>
      </div>
    </div>
  )
}


