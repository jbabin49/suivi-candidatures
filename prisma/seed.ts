import { prisma } from "@/lib/prisma";
import bcrypt from "bcryptjs";

async function main() {
  // Créer un utilisateur par défaut
  const hashedPassword = await bcrypt.hash("admin123", 10);
  
  const user = await prisma.user.upsert({
    where: { username: "admin" },
    update: {},
    create: {
      username: "admin",
      password: hashedPassword,
    },
  });

  console.log("✅ Utilisateur créé:");
  console.log("   Username: admin");
  console.log("   Password: admin123");
  console.log("\n⚠️  CHANGEZ CE MOT DE PASSE EN PRODUCTION !");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
