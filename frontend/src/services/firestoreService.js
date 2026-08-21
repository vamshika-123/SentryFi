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

/**
 * Creates a new scan record in Firestore.
 */
export async function createScanRecord(scanData) {
  try {
    const docRef = await addDoc(collection(db, SCANS_COLLECTION), {
      ...scanData,
      createdAt: serverTimestamp()
    });
    return docRef.id;
  } catch (error) {
    console.error("Error adding scan record: ", error);
    throw error;
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
    return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
  } catch (error) {
    console.error("Error getting recent scans: ", error);
    throw error;
  }
}

/**
 * Subscribes to real-time updates for a user's scans.
 */
export function subscribeToUserScans(userId, callback, limitCount = 50) {
  const q = query(
    collection(db, SCANS_COLLECTION),
    where("userId", "==", userId),
    orderBy("createdAt", "desc"),
    limit(limitCount)
  );

  return onSnapshot(q, (querySnapshot) => {
    const scans = querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    callback(scans);
  }, (error) => {
    console.error("Error subscribing to scans: ", error);
  });
}

/**
 * Deletes a scan record. Note: Associated storage file deletion handled separately if needed.
 */
export async function deleteScanRecord(scanId) {
  try {
    await deleteDoc(doc(db, SCANS_COLLECTION, scanId));
  } catch (error) {
    console.error("Error deleting scan record: ", error);
    throw error;
  }
}
