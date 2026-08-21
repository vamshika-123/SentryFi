import { 
  collection, 
  addDoc, 
  query, 
  where, 
  orderBy, 
  limit, 
  onSnapshot, 
  deleteDoc, 
  doc, 
  serverTimestamp, 
  getDocs 
} from "firebase/firestore";
import { db } from "../config/firebase";

const SCANS_COLLECTION = "scans";
const LOCAL_STORAGE_SCANS_KEY = "sentryfi_mock_scans";

// Event bus for real-time local updates when fallback is used
const localScanListeners = new Set();

function notifyLocalListeners(scans) {
  localScanListeners.forEach(cb => {
    try {
      cb(scans);
    } catch (e) {
      console.error("Listener error:", e);
    }
  });
}

function getLocalScans(userId) {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_SCANS_KEY);
    const all = raw ? JSON.parse(raw) : [];
    return all.filter(s => !userId || s.userId === userId);
  } catch {
    return [];
  }
}

function saveLocalScan(scanData) {
  const scans = getLocalScans();
  const newScan = {
    id: `scan_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
    ...scanData,
    createdAt: {
      toDate: () => new Date(),
      seconds: Math.floor(Date.now() / 1000)
    }
  };
  scans.unshift(newScan);
  localStorage.setItem(LOCAL_STORAGE_SCANS_KEY, JSON.stringify(scans));
  notifyLocalListeners(scans.filter(s => s.userId === scanData.userId));
  return newScan.id;
}

/**
 * Creates a new scan record in Firestore (with LocalStorage fallback).
 */
export async function createScanRecord(scanData) {
  try {
    const docRef = await addDoc(collection(db, SCANS_COLLECTION), {
      ...scanData,
      createdAt: serverTimestamp()
    });
    return docRef.id;
  } catch (error) {
    console.warn("Firestore write failed, falling back to local session store:", error?.message);
    return saveLocalScan(scanData);
  }
}

/**
 * Retrieves a user's recent scans statically.
 */
export async function getRecentScans(userId, limitCount = 10) {
  try {
    const q = query(
      collection(db, SCANS_COLLECTION),
      where("userId", "==", userId),
      orderBy("createdAt", "desc"),
      limit(limitCount)
    );
    const querySnapshot = await getDocs(q);
    const results = querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    if (results.length === 0) {
      return getLocalScans(userId).slice(0, limitCount);
    }
    return results;
  } catch (error) {
    console.warn("Firestore query failed, using local session store:", error?.message);
    return getLocalScans(userId).slice(0, limitCount);
  }
}

/**
 * Subscribes to real-time updates for a user's scans.
 */
export function subscribeToUserScans(userId, callback, limitCount = 50) {
  try {
    const q = query(
      collection(db, SCANS_COLLECTION),
      where("userId", "==", userId),
      orderBy("createdAt", "desc"),
      limit(limitCount)
    );

    const unsubscribe = onSnapshot(q, (querySnapshot) => {
      const scans = querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
      callback(scans);
    }, (error) => {
      console.warn("Firestore realtime subscription failed, using local mock listener:", error?.message);
      // Immediately provide local items
      callback(getLocalScans(userId).slice(0, limitCount));
    });

    // Also register local listener for non-firebase additions
    const localCb = (allScans) => {
      callback(allScans.filter(s => s.userId === userId).slice(0, limitCount));
    };
    localScanListeners.add(localCb);

    return () => {
      if (typeof unsubscribe === "function") unsubscribe();
      localScanListeners.delete(localCb);
    };
  } catch (error) {
    console.warn("Real-time listener setup fallback:", error?.message);
    callback(getLocalScans(userId).slice(0, limitCount));
    const localCb = (allScans) => {
      callback(allScans.filter(s => s.userId === userId).slice(0, limitCount));
    };
    localScanListeners.add(localCb);
    return () => {
      localScanListeners.delete(localCb);
    };
  }
}

/**
 * Deletes a scan record.
 */
export async function deleteScanRecord(scanId) {
  try {
    await deleteDoc(doc(db, SCANS_COLLECTION, scanId));
  } catch (error) {
    console.warn("Firestore delete failed, deleting from local session store:", error?.message);
  }
  // Also delete from local store
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_SCANS_KEY);
    if (raw) {
      const all = JSON.parse(raw).filter(s => s.id !== scanId);
      localStorage.setItem(LOCAL_STORAGE_SCANS_KEY, JSON.stringify(all));
      notifyLocalListeners(all);
    }
  } catch (e) {
    console.error("Failed to delete local scan", e);
  }
}
