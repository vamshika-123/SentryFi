import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "mock_api_key",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "mock_auth_domain",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "mock_project_id",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "mock_storage_bucket",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "mock_sender_id",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "mock_app_id",
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || "mock_measurement_id"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase services
export const auth = getAuth(app);
export const db = getFirestore(app);

export default app;
