import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getServerSession(authOptions);

    if (!session) {
      return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
    }

    const { id } = await params;

    const application = await prisma.application.findUnique({
      where: { id },
      include: { reminders: true },
    });

    if (!application) {
      return NextResponse.json(
        { error: "Candidature non trouvée" },
        { status: 404 }
      );
    }

    // Vérifier que l'utilisateur est propriétaire
    if (application.userId !== session.user.id) {
      return NextResponse.json({ error: "Non autorisé" }, { status: 403 });
    }

    return NextResponse.json(application);
  } catch (error) {
    console.error("Erreur récupération candidature:", error);
    return NextResponse.json(
      { error: "Erreur lors de la récupération" },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getServerSession(authOptions);

    if (!session) {
      return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
    }

    const { id } = await params;
    const data = await request.json();

    // Vérifier que l'utilisateur est propriétaire
    const existingApp = await prisma.application.findUnique({
      where: { id },
    });

    if (!existingApp) {
      return NextResponse.json(
        { error: "Candidature non trouvée" },
        { status: 404 }
      );
    }

    if (existingApp.userId !== session.user.id) {
      return NextResponse.json({ error: "Non autorisé" }, { status: 403 });
    }

    // Supprimer les anciens rappels et en créer de nouveaux
    await prisma.reminder.deleteMany({
      where: { applicationId: id },
    });

    const application = await prisma.application.update({
      where: { id },
      data: {
        company: data.company,
        position: data.position,
        status: data.status || "applied",
        applicationDate: new Date(data.applicationDate),
        notes: data.notes || null,
        contactEmail: data.contactEmail || null,
        contactPhone: data.contactPhone || null,
        salary: data.salary || null,
        location: data.location || null,
        url: data.url || null,
        applicationType: data.applicationType || "response",
        jobType: data.jobType || "job",
        contractType: data.contractType || null,
        coverLetterPath: data.coverLetterPath || null,
        companyLogoPath: data.companyLogoPath || null,
        reminders: {
          create: data.reminders
            ?.filter((r: any) => r.title && r.date)
            .map((r: any) => ({
              title: r.title,
              date: new Date(r.date),
            })) || [],
        },
      },
      include: { reminders: true },
    });

    return NextResponse.json(application);
  } catch (error) {
    console.error("Erreur mise à jour candidature:", error);
    return NextResponse.json(
      { error: "Erreur lors de la mise à jour" },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getServerSession(authOptions);

    if (!session) {
      return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
    }

    const { id } = await params;

    // Vérifier que l'utilisateur est propriétaire
    const existingApp = await prisma.application.findUnique({
      where: { id },
    });

    if (!existingApp) {
      return NextResponse.json(
        { error: "Candidature non trouvée" },
        { status: 404 }
      );
    }

    if (existingApp.userId !== session.user.id) {
      return NextResponse.json({ error: "Non autorisé" }, { status: 403 });
    }

    await prisma.application.delete({
      where: { id },
    });

    return NextResponse.json({ message: "Candidature supprimée" });
  } catch (error) {
    console.error("Erreur suppression candidature:", error);
    return NextResponse.json(
      { error: "Erreur lors de la suppression" },
      { status: 500 }
    );
  }
}
