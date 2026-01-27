import { apiFetch } from "../api";

export async function login(username, password) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);

  return data;
}

export async function me() {
  return apiFetch("/auth/me");
}

export async function logout() {
  const refresh = localStorage.getItem("refresh_token");

  try {
    if (refresh) {  
      window.location.href =
      "http://localhost:8082/realms/chaM3leon_realm/protocol/openid-connect/logout" +
      "?client_id=cham3leon_frontend" +
      "&post_logout_redirect_uri=http://localhost:3000/login";
       }
      await apiFetch("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refresh }),
      });
    }
    finally {
    // Pulizia locale SEMPRE, anche se il backend fallisce
    localStorage.clear();
  
  }
}

export async function refreshToken() {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) {
    throw new Error("No refresh token available");
  } 
  const data = await apiFetch("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refresh }),
  });
  localStorage.setItem("access_token", data.access_token);
  return data;
}

export async function createUser(user) {
  return apiFetch("/auth/user", {
    method: "POST",
    body: JSON.stringify(user),
  });
}


export async function deleteUser(username) {
  await apiFetch("/auth/user/delete", {
    method: "DELETE",
    body: JSON.stringify({ username }),
  });
}

export async function getPublicKeys() {
  return apiFetch("/auth/keys");
}

