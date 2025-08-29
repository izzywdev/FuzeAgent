import React from 'react'

export function InlineCss(): JSX.Element {
  return (
    <style>
      {`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}
    </style>
  )
}


