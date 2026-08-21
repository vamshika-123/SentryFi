import React, { createContext, useContext, useState, useEffect } from "react";
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup
} from "firebase/auth";
import { auth } from "../config/firebase";

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

const LOCAL_STORAGE_KEY = "sentryfi_user_session";

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  // Helper to humanize Firebase error codes
  function formatAuthError(error) {
    if (!error) return "An unknown error occurred.";
    const code = error.code || "";
    if (code.includes("invalid-api-key") || code.includes("api-key-not-valid")) {
      return "Firebase API Key is unconfigured or invalid. Please contact your administrator.";
    }
    if (code.includes("user-not-found") || code.includes("invalid-credential")) {
      return "Invalid email or password. Please verify your credentials or create an account.";
    }
    if (code.includes("wrong-password")) {
      return "Incorrect password. Please try again.";
    }
    if (code.includes("email-already-in-use")) {
      return "An account with this email already exists. Please sign in instead.";
    }
    if (code.includes("weak-password")) {
      return "Password is too weak. Please use at least 6 characters.";
    }
    if (code.includes("invalid-email")) {
      return "Please enter a valid email address.";
    }
    if (code.includes("popup-closed-by-user")) {
      return "Sign in popup was closed before completing.";
    }
    return error.message || "Authentication failed. Please try again.";
  }

  async function signUp(email, password) {
    try {
      const res = await createUserWithEmailAndPassword(auth, email, password);
      const userObj = {
        uid: res.user.uid,
        email: res.user.email,
        displayName: res.user.displayName || email.split("@")[0]
      };
      setCurrentUser(userObj);
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(userObj));
      return userObj;
    } catch (err) {
      const errorMsg = formatAuthError(err);
      throw new Error(errorMsg);
    }
  }

  async function login(email, password) {
    try {
      const res = await signInWithEmailAndPassword(auth, email, password);
      const userObj = {
        uid: res.user.uid,
        email: res.user.email,
        displayName: res.user.displayName || email.split("@")[0]
      };
      setCurrentUser(userObj);
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(userObj));
      return userObj;
    } catch (err) {
      const errorMsg = formatAuthError(err);
      throw new Error(errorMsg);
    }
  }

  async function loginWithGoogle() {
    try {
      const provider = new GoogleAuthProvider();
      const res = await signInWithPopup(auth, provider);
      const userObj = {
        uid: res.user.uid,
        email: res.user.email,
        displayName: res.user.displayName || "Google User",
        photoURL: res.user.photoURL
      };
      setCurrentUser(userObj);
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(userObj));
      return userObj;
    } catch (err) {
      const errorMsg = formatAuthError(err);
      throw new Error(errorMsg);
    }
  }


  async function logout() {
    try {
      await signOut(auth);
    } catch (e) {
      console.error("Sign out error", e);
    }
    setCurrentUser(null);
    localStorage.removeItem(LOCAL_STORAGE_KEY);
  }

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        const userObj = {
          uid: user.uid,
          email: user.email,
          displayName: user.displayName || user.email?.split("@")[0],
          photoURL: user.photoURL
        };
        setCurrentUser(userObj);
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(userObj));
      } else {
        setCurrentUser(null);
        localStorage.removeItem(LOCAL_STORAGE_KEY);
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const value = {
    currentUser,
    login,
    signUp,
    loginWithGoogle,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}
