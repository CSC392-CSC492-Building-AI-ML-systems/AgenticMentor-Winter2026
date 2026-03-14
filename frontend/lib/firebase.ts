import firebase from "firebase/compat/app";
import "firebase/compat/auth";

function getFirebaseConfig(): Record<string, string | undefined> {
  // Use Firebase's auth domain (HTTPS). For localhost we must NOT use our origin as authDomain
  // or the SDK redirects to https://localhost:3000 and causes ERR_SSL_PROTOCOL_ERROR.
  return {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "mentor-e704f.firebaseapp.com",
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  };
}

function getFirebaseApp(): firebase.app.App | null {
  if (firebase.apps.length === 0) {
    const config = getFirebaseConfig();
    if (!config.apiKey || !config.projectId) return null;
    return firebase.initializeApp(config);
  }
  return firebase.apps[0];
}

export function getFirebaseAuth(): firebase.auth.Auth | null {
  try {
    const app = getFirebaseApp();
    return app ? app.auth() : null;
  } catch {
    return null;
  }
}

export const googleProvider = new firebase.auth.GoogleAuthProvider();
export const githubProvider = new firebase.auth.GithubAuthProvider();
