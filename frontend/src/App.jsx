import React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useStore } from './store/index.js'
import SetupPage from './components/setup/SetupPage.jsx'
import ChatPage from './components/assessment/ChatPage.jsx'
import ReportPage from './components/report/ReportPage.jsx'

const PAGE_VARIANTS = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] } },
  exit:    { opacity: 0, y: -8, transition: { duration: 0.2 } },
}

export default function App() {
  const { activeView } = useStore()

  return (
    <AnimatePresence mode="wait">
      {activeView === 'setup' && (
        <motion.div key="setup" {...PAGE_VARIANTS} style={{ minHeight: '100vh' }}>
          <SetupPage />
        </motion.div>
      )}
      {activeView === 'chat' && (
        <motion.div key="chat" {...PAGE_VARIANTS} style={{ height: '100vh' }}>
          <ChatPage />
        </motion.div>
      )}
      {activeView === 'report' && (
        <motion.div key="report" {...PAGE_VARIANTS} style={{ minHeight: '100vh' }}>
          <ReportPage />
        </motion.div>
      )}
    </AnimatePresence>
  )
}