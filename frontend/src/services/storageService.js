import { ref, uploadBytesResumable, getDownloadURL, deleteObject } from "firebase/storage";
import { storage } from "../config/firebase";

const ALLOWED_MIME_TYPES = ["application/pdf", "image/png", "image/jpeg", "image/jpg"];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

/**
 * Uploads a document (invoice or audit) to Firebase Storage
 * 
 * @param {File} file - The file to upload
 * @param {string} userId - Current user's ID
 * @param {string} folderType - e.g., 'invoices' or 'compliance'
 * @param {function} onProgress - Callback for upload progress
 * @returns {Promise<string>} - Download URL
 */
export async function uploadScanDocument(file, userId, folderType, onProgress = null) {
  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    throw new Error("Invalid file type. Only PDF, PNG, and JPEG are allowed.");
  }

  if (file.size > MAX_FILE_SIZE) {
    throw new Error("File exceeds the maximum limit of 10MB.");
  }

  const timestamp = Date.now();
  const safeFileName = file.name.replace(/[^a-zA-Z0-9.\-_]/g, '_');
  const filePath = `uploads/${userId}/${folderType}/${timestamp}_${safeFileName}`;
  
  const storageRef = ref(storage, filePath);
  const uploadTask = uploadBytesResumable(storageRef, file);

  return new Promise((resolve, reject) => {
    uploadTask.on(
      "state_changed",
      (snapshot) => {
        if (onProgress) {
          const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
          onProgress(progress);
        }
      },
      (error) => {
        console.error("Upload failed: ", error);
        reject(error);
      },
      async () => {
        try {
          const downloadURL = await getDownloadURL(uploadTask.snapshot.ref);
          resolve({ downloadURL, filePath });
        } catch (error) {
          reject(error);
        }
      }
    );
  });
}

/**
 * Deletes a file from Cloud Storage given its path
 */
export async function deleteStorageFile(filePath) {
  try {
    const fileRef = ref(storage, filePath);
    await deleteObject(fileRef);
  } catch (error) {
    console.error("Error deleting file: ", error);
    throw error;
  }
}
