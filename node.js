const admin = require("firebase-admin");
const serviceAccount = require("./serviceAccountKey.json");
const registry = require("./registry.json");

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

async function uploadRegistry() {
  const collection = db.collection("registry");

  for (const key in registry) {
    const data = registry[key];

    await collection.doc(key).set(data);
    console.log(`Uploaded: ${key}`);
  }

  console.log("All registry data uploaded!");
}

uploadRegistry();