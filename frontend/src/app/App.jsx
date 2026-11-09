/**
 * App.jsx — Root component. Mounts RouterProvider only.
 * No JSX besides wiring; keep this file minimal.
 */
import { RouterProvider } from 'react-router-dom';
import { router } from './app.routes';

const App = () => <RouterProvider router={router} />;

export default App;
