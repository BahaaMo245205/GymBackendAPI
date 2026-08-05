const BACKEND_URL = "http://localhost:8000";

async function refreshAccessToken() {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return null;

    try {
        const res = await fetch(`${BACKEND_URL}/v1/api/user/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        const data = await res.json();

        if (!res.ok) {
            localStorage.clear();
            return null;
        }

        localStorage.setItem("access_token", data.access_token);
        return data.access_token;
    } catch (err) {
        console.error("Refresh failed:", err);
        return null;
    }
}