import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { existsSync } from "fs";

const UPLOAD_DIR = join(process.cwd(), "public/uploads");

async function ensureUploadDir() {
  if (!existsSync(UPLOAD_DIR)) {
    await mkdir(UPLOAD_DIR, { recursive: true });
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session) {
      return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
    }

    const formData = await request.formData();
    const file = formData.get("file") as File;
    const fileType = formData.get("type") as string; // 'coverLetter' ou 'logo'

    if (!file) {
      return NextResponse.json(
        { error: "Pas de fichier trouvé" },
        { status: 400 }
      );
    }

    // Validation du type de fichier
    const validTypes: Record<string, string[]> = {
      coverLetter: ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
      logo: ["image/jpeg", "image/png", "image/gif", "image/webp"],
    };

    if (!validTypes[fileType]?.includes(file.type)) {
      return NextResponse.json(
        { error: "Type de fichier non autorisé" },
        { status: 400 }
      );
    }

    // Limite de taille
    const maxSize = fileType === "coverLetter" ? 10 * 1024 * 1024 : 5 * 1024 * 1024; // 10MB pour lettre, 5MB pour logo
    if (file.size > maxSize) {
      return NextResponse.json(
        { error: "Fichier trop volumineux" },
        { status: 400 }
      );
    }

    await ensureUploadDir();

    // Générer un nom de fichier unique
    const timestamp = Date.now();
    const randomStr = Math.random().toString(36).substring(7);
    const ext = file.name.split(".").pop();
    const filename = `${session.user.id}_${fileType}_${timestamp}_${randomStr}.${ext}`;

    // Sauvegarder le fichier
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);
    
    const filepath = join(UPLOAD_DIR, filename);
    await writeFile(filepath, buffer);

    // Retourner le chemin relatif
    const relativePath = `/uploads/${filename}`;

    return NextResponse.json({ path: relativePath });
  } catch (error) {
    console.error("Erreur upload:", error);
    return NextResponse.json(
      { error: "Erreur lors de l'upload" },
      { status: 500 }
    );
  }
}
