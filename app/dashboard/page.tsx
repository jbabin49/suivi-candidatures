"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import LogoutButton from "@/components/LogoutButton";
import Link from "next/link";

interface Application {
  id: string;
  company: string;
  position: string;
  status: string;
  applicationDate: string;
  notes: string | null;
  salary: string | null;
  location: string | null;
  url: string | null;
  applicationType: string;
  jobType: string;
  contractType: string | null;
  coverLetterPath: string | null;
  companyLogoPath: string | null;
  reminders: { id: string; title: string; date: string; completed: boolean }[];
}

interface Stats {
  total: number;
  applied: number;
  interview: number;
  accepted: number;
  rejected: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<Application[]>([]);
  const [username, setUsername] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats>({
    total: 0,
    applied: 0,
    interview: 0,
    accepted: 0,
    rejected: 0,
  });
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    fetchProfile();
    fetchApplications();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await fetch("/api/user/profile");
      if (response.ok) {
        const data = await response.json();
        setUsername(data.username);
      }
    } catch (err) {
      console.error("Erreur profil:", err);
    }
  };

  const fetchApplications = async () => {
    try {
      const response = await fetch("/api/applications");
      if (!response.ok) throw new Error("Erreur");
      const data = await response.json();
      setApplications(data);

      // Calculer les stats
      const newStats: Stats = {
        total: data.length,
        applied: data.filter((a: Application) => a.status === "applied").length,
        interview: data.filter((a: Application) => a.status === "interview")
          .length,
        accepted: data.filter((a: Application) => a.status === "accepted").length,
        rejected: data.filter((a: Application) => a.status === "rejected").length,
      };
      setStats(newStats);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (appId: string) => {
    if (!confirm("Êtes-vous sûr de vouloir supprimer cette candidature ?")) {
      return;
    }

    setDeleting(appId);
    try {
      const response = await fetch(`/api/applications/${appId}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("Erreur de suppression");

      setApplications(applications.filter((a) => a.id !== appId));
      router.refresh();
    } catch (err) {
      alert("Erreur lors de la suppression");
    } finally {
      setDeleting(null);
    }
  };

  const filteredApplications = filterStatus
    ? applications.filter((a) => a.status === filterStatus)
    : applications;

  const upcomingReminders = filteredApplications
    .flatMap((app) =>
      app.reminders.map((r) => ({
        ...r,
        company: app.company,
        position: app.position,
      }))
    )
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .slice(0, 5);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <p className="text-gray-600 dark:text-gray-400">Chargement...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <nav className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                Suivi Candidatures
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              {username && (
                <div className="flex items-center space-x-3">
                  <span className="text-gray-700 dark:text-gray-300">
                    Bienvenue, <strong>{username}</strong>
                  </span>
                  <Link
                    href="/dashboard/settings"
                    className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300 text-sm"
                  >
                    ⚙️ Paramètres
                  </Link>
                </div>
              )}
              <LogoutButton />
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Stats - Cliquables pour filtrer */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6 px-4 sm:px-0">
          <button
            onClick={() => setFilterStatus(null)}
            className={`p-4 rounded-lg shadow cursor-pointer transition ${
              filterStatus === null
                ? "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900"
                : "bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            <p className={`text-sm ${filterStatus === null ? "text-gray-300 dark:text-gray-700" : "text-gray-600 dark:text-gray-400"}`}>Total</p>
            <p className={`text-2xl font-bold ${filterStatus === null ? "text-white dark:text-gray-900" : "text-gray-900 dark:text-white"}`}>
              {stats.total}
            </p>
          </button>
          <button
            onClick={() => setFilterStatus("applied")}
            className={`p-4 rounded-lg shadow cursor-pointer transition ${
              filterStatus === "applied"
                ? "bg-blue-600 text-white"
                : "bg-blue-50 dark:bg-blue-900 hover:bg-blue-100 dark:hover:bg-blue-800"
            }`}
          >
            <p className={`text-sm ${filterStatus === "applied" ? "text-blue-100" : "text-blue-600 dark:text-blue-300"}`}>
              Postulées
            </p>
            <p className="text-2xl font-bold text-blue-900 dark:text-white">
              {stats.applied}
            </p>
          </button>
          <button
            onClick={() => setFilterStatus("interview")}
            className={`p-4 rounded-lg shadow cursor-pointer transition ${
              filterStatus === "interview"
                ? "bg-yellow-600 text-white"
                : "bg-yellow-50 dark:bg-yellow-900 hover:bg-yellow-100 dark:hover:bg-yellow-800"
            }`}
          >
            <p className={`text-sm ${filterStatus === "interview" ? "text-yellow-100" : "text-yellow-600 dark:text-yellow-300"}`}>
              Entretiens
            </p>
            <p className="text-2xl font-bold text-yellow-900 dark:text-white">
              {stats.interview}
            </p>
          </button>
          <button
            onClick={() => setFilterStatus("accepted")}
            className={`p-4 rounded-lg shadow cursor-pointer transition ${
              filterStatus === "accepted"
                ? "bg-green-600 text-white"
                : "bg-green-50 dark:bg-green-900 hover:bg-green-100 dark:hover:bg-green-800"
            }`}
          >
            <p className={`text-sm ${filterStatus === "accepted" ? "text-green-100" : "text-green-600 dark:text-green-300"}`}>
              Acceptées
            </p>
            <p className="text-2xl font-bold text-green-900 dark:text-white">
              {stats.accepted}
            </p>
          </button>
          <button
            onClick={() => setFilterStatus("rejected")}
            className={`p-4 rounded-lg shadow cursor-pointer transition ${
              filterStatus === "rejected"
                ? "bg-red-600 text-white"
                : "bg-red-50 dark:bg-red-900 hover:bg-red-100 dark:hover:bg-red-800"
            }`}
          >
            <p className={`text-sm ${filterStatus === "rejected" ? "text-red-100" : "text-red-600 dark:text-red-300"}`}>
              Refusées
            </p>
            <p className="text-2xl font-bold text-red-900 dark:text-white">
              {stats.rejected}
            </p>
          </button>
        </div>

        {/* Rappels */}
        {upcomingReminders.length > 0 && (
          <div className="mb-6 px-4 sm:px-0">
            <div className="bg-yellow-50 dark:bg-yellow-900 border-l-4 border-yellow-400 p-4 rounded">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-yellow-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                    Rappels à venir
                  </h3>
                  <div className="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
                    <ul className="list-disc list-inside space-y-1">
                      {upcomingReminders.map((reminder: any) => (
                        <li key={reminder.id}>
                          <strong>{reminder.company}</strong> -{" "}
                          {reminder.title} (
                          {new Date(reminder.date).toLocaleDateString("fr-FR")})
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="mb-6 px-4 sm:px-0">
          <Link
            href="/dashboard/add"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            + Ajouter une candidature
          </Link>
        </div>

        {/* Liste des candidatures */}
        <div className="px-4 sm:px-0">
          <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredApplications.length === 0 ? (
                <li className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  {filterStatus
                    ? `Aucune candidature avec le statut "${filterStatus}". `
                    : "Aucune candidature pour le moment. "}
                  <Link
                    href="/dashboard/add"
                    className="text-indigo-600 hover:text-indigo-500"
                  >
                    Ajoutez-en une !
                  </Link>
                </li>
              ) : (
                filteredApplications.map((app) => (
                  <li key={app.id}>
                    <div className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          {/* Logo si présent */}
                          {app.companyLogoPath && (
                            <div className="flex-shrink-0 mb-2">
                              <img
                                src={app.companyLogoPath}
                                alt={app.company}
                                className="h-12 w-12 object-contain"
                              />
                            </div>
                          )}
                          <div className="flex items-center justify-between">
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                              {app.position}
                            </h3>
                            <span
                              className={`px-2 py-1 text-xs font-semibold rounded-full ${
                                app.status === "applied"
                                  ? "bg-blue-100 text-blue-800"
                                  : app.status === "interview"
                                  ? "bg-yellow-100 text-yellow-800"
                                  : app.status === "accepted"
                                  ? "bg-green-100 text-green-800"
                                  : "bg-red-100 text-red-800"
                              }`}
                            >
                              {app.status === "applied"
                                ? "Postulée"
                                : app.status === "interview"
                                ? "Entretien"
                                : app.status === "accepted"
                                ? "Acceptée"
                                : "Refusée"}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                            {app.company}
                          </p>

                          {/* Type candidature et type poste */}
                          <div className="mt-2 flex gap-2 flex-wrap">
                            <span className="inline-block px-2 py-1 text-xs bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 rounded">
                              {app.applicationType === "response"
                                ? "Offre"
                                : "Spontanée"}
                            </span>
                            <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">
                              {app.jobType === "job" ? "Emploi" : "Stage"}
                            </span>
                            {app.contractType && (
                              <span className="inline-block px-2 py-1 text-xs bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200 rounded">
                                {app.contractType === "cdi"
                                  ? "CDI"
                                  : app.contractType === "cdd"
                                  ? "CDD"
                                  : "Intérim"}
                              </span>
                            )}
                          </div>

                          {app.location && (
                            <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                              📍 {app.location}
                            </p>
                          )}
                          {app.salary && (
                            <p className="text-sm text-gray-500 dark:text-gray-500">
                              💰 {app.salary}
                            </p>
                          )}
                          <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
                            Postulée le{" "}
                            {new Date(app.applicationDate).toLocaleDateString(
                              "fr-FR"
                            )}
                          </p>

                          {/* Lettres de motivation */}
                          <div className="mt-2 flex gap-2">
                            {app.coverLetterPath && (
                              <a
                                href={app.coverLetterPath}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 underline"
                              >
                                📄 Lettre de motivation
                              </a>
                            )}
                            {app.url && (
                              <a
                                href={app.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 underline"
                              >
                                🔗 Offre
                              </a>
                            )}
                          </div>

                          {app.notes && (
                            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                              {app.notes}
                            </p>
                          )}
                          {app.reminders.length > 0 && (
                            <div className="mt-2">
                              <p className="text-xs text-gray-500 dark:text-gray-500">
                                ⏰ {app.reminders.length} rappel(s) actif(s)
                              </p>
                            </div>
                          )}

                          {/* Actions */}
                          <div className="mt-4 flex gap-2">
                            <Link
                              href={`/dashboard/edit/${app.id}`}
                              className="text-sm px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700"
                            >
                              Modifier
                            </Link>
                            <button
                              onClick={() => handleDelete(app.id)}
                              disabled={deleting === app.id}
                              className="text-sm px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                            >
                              {deleting === app.id ? "Suppression..." : "Supprimer"}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>
      </main>
    </div>
  );
}
