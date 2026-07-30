import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyDKQU1xQlH_v6Y79-69phr2jsQ4QWuWe_o",
  authDomain: "ai-business-platform-e7043.firebaseapp.com",
  projectId: "ai-business-platform-e7043",
  storageBucket: "ai-business-platform-e7043.firebasestorage.app",
  messagingSenderId: "983773208764",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
