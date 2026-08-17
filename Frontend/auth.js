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

async function checkUserActive(token) {
    try {
        const res = await fetch(`${BACKEND_URL}/v1/api/user/is-active`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
 
        if (res.status === 401) { // Unauthorized (Token expired)
            console.log("Access token expired, trying to refresh...");
            const newAccessToken = await refreshAccessToken();
            if (!newAccessToken) { // Refresh failed
                localStorage.clear();
                window.location.href = "login.html";
                return false;
            }
            return await checkUserActive(newAccessToken); // Retry with new token
        }
 
        if (!res.ok) { // Other errors (e.g., 403 Forbidden/Banned)
            const data = await res.json();
            alert(data.detail || "حدث خطأ أو أن الحساب محظور.");
            localStorage.clear();
            window.location.href = "login.html";
            return false;
        }
        return true; // User is active
    } catch (err) {
        console.error("Failed to check user status:", err);
        alert("لا يمكن الاتصال بالخادم للتحقق من حالة الحساب.");
        return false; // Indicate failure
    }
}