import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session) {
      return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
    }

    const data = await request.json();

    const application = await prisma.application.create({
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
        userId: session.user.id,
        reminders: {
          create: data.reminders
            ?.filter((r: any) => r.title && r.date)
            .map((r: any) => ({
              title: r.title,
              date: new Date(r.date),
            })) || [],
        },
      },
    });

    return NextResponse.json(application);
  } catch (error) {
    console.error("Erreur création candidature:", error);
    return NextResponse.json(
      { error: "Erreur lors de la création" },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    const session = await getServerSession(authOptions);

    if (!session) {
      return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
    }

    const applications = await prisma.application.findMany({
      where: { userId: session.user.id },
      include: { reminders: true },
      orderBy: { createdAt: "desc" },
    });

    return NextResponse.json(applications);
  } catch (error) {
    console.error("Erreur récupération candidatures:", error);
    return NextResponse.json(
      { error: "Erreur lors de la récupération" },
      { status: 500 }
    );
  }
}
