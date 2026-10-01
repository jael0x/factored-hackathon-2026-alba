import { Navigate, Route, Routes } from "react-router";

import { Aurora } from "./components/Aurora";
import { RequireSession } from "./components/RequireSession";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { HOME_PATH, LOGIN_PATH } from "./routes";

export function App() {
  return (
    <>
      <Aurora />
      <Routes>
        <Route path={LOGIN_PATH.customer} element={<Login />} />
        <Route
          path={HOME_PATH.customer}
          element={
            <RequireSession role="customer">
              <Home />
            </RequireSession>
          }
        />
        <Route path="*" element={<Navigate to={HOME_PATH.customer} replace />} />
      </Routes>
    </>
  );
}
