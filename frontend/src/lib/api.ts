import axios from "axios";

// All API calls go to the Next.js BFF proxy (/api/...) — never directly to the backend.
// The proxy (src/app/api/[...path]/route.ts) forwards them to FastAPI internally.
const api = axios.create({
  baseURL: "",
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        window.location.href = "/";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
