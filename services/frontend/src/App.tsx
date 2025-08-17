import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Agents } from './pages/Agents'
import { Teams } from './pages/Teams'
import { Layout } from './components/Layout'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/teams" element={<Teams />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
