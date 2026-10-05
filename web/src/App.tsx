import { Navigate, Route, Routes } from "react-router";

import { Aurora } from "./components/Aurora";
import { RequireSession } from "./components/RequireSession";
import { Case } from "./pages/Case";
import { ConsultantHome } from "./pages/ConsultantHome";
import { ConsultantLogin } from "./pages/ConsultantLogin";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { CASE_PATH, HOME_PATH, LOGIN_PATH } from "./routes";

export function App() {
  return (
    <>
      <Aurora />
      <Routes>
        <Route path={LOGIN_PATH.customer} element={<Login />} />
        <Route path={LOGIN_PATH.consultant} element={<ConsultantLogin />} />
        <Route
          path={HOME_PATH.customer}
          element={
            <RequireSession role="customer">
              <Home />
            </RequireSession>
          }
        />
        <Route
          path={`${CASE_PATH}/:processId?`}
          element={
            <RequireSession role="customer">
              <Case />
            </RequireSession>
          }
        />
        <Route
          path={HOME_PATH.consultant}
          element={
            <RequireSession role="consultant">
              <ConsultantHome />
            </RequireSession>
          }
        />
        <Route path="*" element={<Navigate to={HOME_PATH.customer} replace />} />
      </Routes>
    </>
  );
}
