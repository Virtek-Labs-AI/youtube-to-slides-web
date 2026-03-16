import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  withCredentials: true, // Send the httpOnly cookie on every request
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
