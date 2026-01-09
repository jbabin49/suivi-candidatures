-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Application" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "company" TEXT NOT NULL,
    "position" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'applied',
    "applicationDate" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "notes" TEXT,
    "contactEmail" TEXT,
    "contactPhone" TEXT,
    "salary" TEXT,
    "location" TEXT,
    "url" TEXT,
    "applicationType" TEXT NOT NULL DEFAULT 'response',
    "jobType" TEXT NOT NULL DEFAULT 'job',
    "contractType" TEXT,
    "coverLetterPath" TEXT,
    "companyLogoPath" TEXT,
    "userId" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "Application_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_Application" ("applicationDate", "company", "contactEmail", "contactPhone", "createdAt", "id", "location", "notes", "position", "salary", "status", "updatedAt", "url", "userId") SELECT "applicationDate", "company", "contactEmail", "contactPhone", "createdAt", "id", "location", "notes", "position", "salary", "status", "updatedAt", "url", "userId" FROM "Application";
DROP TABLE "Application";
ALTER TABLE "new_Application" RENAME TO "Application";
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
