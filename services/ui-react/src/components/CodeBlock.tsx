import { useState } from 'react'
import { Highlight, themes } from 'prism-react-renderer'
import { CopyToClipboard } from 'react-copy-to-clipboard'
import { FiCopy, FiCheck } from 'react-icons/fi'

interface CodeBlockProps {
  children: string
  language?: string
  title?: string
  showLineNumbers?: boolean
  className?: string
}

export default function CodeBlock({ 
  children, 
  language = 'javascript', 
  title,
  showLineNumbers = true,
  className = ''
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Clean up the code string
  const code = children.trim()

  return (
    <div className={`relative group ${className}`}>
      {title && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800 text-gray-200 text-sm font-medium border-b border-gray-700 rounded-t-lg">
          <span>{title}</span>
          <span className="text-xs text-gray-400 uppercase">{language}</span>
        </div>
      )}
      
      <div className="relative">
        <Highlight
          theme={themes.vsDark}
          code={code}
          language={language}
        >
          {({ className, style, tokens, getLineProps, getTokenProps }) => (
            <pre 
              className={`${className} overflow-x-auto p-4 ${title ? 'rounded-b-lg' : 'rounded-lg'} text-sm`}
              style={style}
            >
              {tokens.map((line, i) => (
                <div key={i} {...getLineProps({ line })}>
                  {showLineNumbers && (
                    <span className="inline-block w-8 text-gray-500 text-right mr-4 select-none">
                      {i + 1}
                    </span>
                  )}
                  {line.map((token, key) => (
                    <span key={key} {...getTokenProps({ token })} />
                  ))}
                </div>
              ))}
            </pre>
          )}
        </Highlight>

        {/* Copy button */}
        <CopyToClipboard text={code} onCopy={handleCopy}>
          <button className="absolute top-2 right-2 p-2 rounded-md bg-gray-700 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-600">
            {copied ? (
              <FiCheck className="w-4 h-4 text-green-400" />
            ) : (
              <FiCopy className="w-4 h-4" />
            )}
          </button>
        </CopyToClipboard>
      </div>
    </div>
  )
}