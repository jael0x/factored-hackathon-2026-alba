import { Navigate, Route, Routes } from "react-router";

import { Aurora } from "./components/Aurora";
import { RequireCustomer } from "./components/RequireCustomer";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";

export function App() {
  return (
    <>
      <Aurora />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireCustomer>
              <Home />
            </RequireCustomer>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
