import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import App from '../App'
import DocsPage from '../pages/DocsPage'
import ApiPlayground from './ApiPlayground'

export default function AppRouter() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/docs/*" element={<DocsPage />} />
        <Route path="/playground" element={<ApiPlayground />} />
      </Routes>
    </Router>
  )
}