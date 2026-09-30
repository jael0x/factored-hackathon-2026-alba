import createClient, { type Middleware } from "openapi-fetch";

import { currentToken, endExpiredSession } from "../session/session";
import type { paths } from "./schema";

const bearer: Middleware = {
  onRequest({ request }) {
    const token = currentToken();
    if (token !== null) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
  onResponse({ request, response }) {
    if (response.status === 401 && request.headers.has("Authorization")) {
      endExpiredSession();
    }
    return response;
  },
};

export const api = createClient<paths>({ baseUrl: "/api" });
api.use(bearer);
