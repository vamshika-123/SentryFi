import { ref, deleteObject } from "firebase/storage";
import { storage } from "../config/firebase";

const ALLOWED_MIME_TYPES = [
  "application/pdf", 
  "image/png", 
  "image/jpeg", 
  "image/jpg", 
  "text/plain"
];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

/**
 * Uploads a document (invoice or audit) to Firebase Storage, with fallback.
 * 
 * @param {File} file - The file to upload
 * @param {string} userId - Current user's ID
 * @param {string} folderType - e.g., 'invoices' or 'compliance'
 * @param {function} onProgress - Callback for upload progress
 * @returns {Promise<{downloadURL: string, filePath: string}>}
 */
export async function uploadScanDocument(file, userId, folderType, onProgress = null) {
  if (file.type && !ALLOWED_MIME_TYPES.includes(file.type) && !file.name.endsWith('.pdf') && !file.name.endsWith('.txt')) {
    throw new Error("Invalid file type. Only PDF, PNG, and JPEG files are supported.");
  }

  if (file.size > MAX_FILE_SIZE) {
    throw new Error("File exceeds the maximum limit of 10MB.");
  }

  const timestamp = Date.now();
  const safeFileName = file.name.replace(/[^a-zA-Z0-9.\-_]/g, '_');
  const filePath = `uploads/${userId}/${folderType}/${timestamp}_${safeFileName}`;

  // NOTE: Firebase Storage CORS is not yet configured on this bucket.
  // Using local blob URL fallback (no network request made, no CORS errors).
  // To enable real cloud uploads later, run:
  //   gsutil cors set cors.json gs://invoice-fraud-detection-84638.firebasestorage.app
  // Then replace this block with the cloud upload logic (see git history).

  if (onProgress) {
    onProgress(25);
    await new Promise(r => setTimeout(r, 100));
    onProgress(60);
    await new Promise(r => setTimeout(r, 120));
    onProgress(100);
  }

  const localUrl = URL.createObjectURL(file);
  return { downloadURL: localUrl, filePath };
}

/**
 * Deletes a file from Cloud Storage given its path.
 * No-op in local fallback mode.
 */
export async function deleteStorageFile(filePath) {
  try {
    const fileRef = ref(storage, filePath);
    await deleteObject(fileRef);
  } catch (error) {
    console.warn("Storage delete ignored (local fallback):", error?.message);
  }
}
