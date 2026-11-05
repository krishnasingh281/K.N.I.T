import { RouterProvider } from 'react-router'
import { Dashboard } from '../features/dashboard/pages/Dashboard'
import "./App.css"
import { router } from './app.routes'

const App = () => {
  return (
    <>
      <RouterProvider router={router}/>
    </>
  )
}

export default App