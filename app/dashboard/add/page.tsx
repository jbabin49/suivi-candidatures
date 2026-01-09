"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function AddApplicationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploadingCoverLetter, setUploadingCoverLetter] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);

  const [formData, setFormData] = useState({
    company: "",
    position: "",
    status: "applied",
    applicationDate: new Date().toISOString().split("T")[0],
    notes: "",
    contactEmail: "",
    contactPhone: "",
    salary: "",
    location: "",
    url: "",
    applicationType: "response",
    jobType: "job",
    contractType: "cdi",
    coverLetterPath: "",
    companyLogoPath: "",
    reminders: [] as { title: string; date: string }[],
  });

  const handleFileUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    fileType: "coverLetter" | "logo"
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (fileType === "coverLetter") {
      setUploadingCoverLetter(true);
    } else {
      setUploadingLogo(true);
    }

    try {
      const formDataUpload = new FormData();
      formDataUpload.append("file", file);
      formDataUpload.append("type", fileType);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formDataUpload,
      });

      if (!response.ok) {
        throw new Error("Erreur lors de l'upload");
      }

      const data = await response.json();

      if (fileType === "coverLetter") {
        setFormData({ ...formData, coverLetterPath: data.path });
      } else {
        setFormData({ ...formData, companyLogoPath: data.path });
      }
    } catch (err) {
      setError("Erreur lors du téléchargement du fichier");
    } finally {
      if (fileType === "coverLetter") {
        setUploadingCoverLetter(false);
      } else {
        setUploadingLogo(false);
      }
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    // Validation: au moins l'email ou le téléphone doit être renseigné
    if (!formData.contactEmail && !formData.contactPhone) {
      setError("Veuillez renseigner au moins l'email ou le téléphone de contact");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("/api/applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error("Erreur lors de l'ajout");
      }

      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setError("Une erreur est survenue");
    } finally {
      setLoading(false);
    }
  };

  const addReminder = () => {
    setFormData({
      ...formData,
      reminders: [...formData.reminders, { title: "", date: "" }],
    });
  };

  const updateReminder = (
    index: number,
    field: "title" | "date",
    value: string
  ) => {
    const newReminders = [...formData.reminders];
    newReminders[index][field] = value;
    setFormData({ ...formData, reminders: newReminders });
  };

  const removeReminder = (index: number) => {
    setFormData({
      ...formData,
      reminders: formData.reminders.filter((_: any, i: number) => i !== index),
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <nav className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link
                href="/dashboard"
                className="text-indigo-600 hover:text-indigo-500"
              >
                ← Retour
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 sm:px-0">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
            Ajouter une candidature
          </h1>

          <form
            onSubmit={handleSubmit}
            className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 space-y-6"
          >
            {/* Informations principales */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="company"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Entreprise *
                </label>
                <input
                  type="text"
                  id="company"
                  required
                  value={formData.company}
                  onChange={(e) =>
                    setFormData({ ...formData, company: e.target.value })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
              </div>

              <div>
                <label
                  htmlFor="position"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Poste *
                </label>
                <input
                  type="text"
                  id="position"
                  required
                  value={formData.position}
                  onChange={(e) =>
                    setFormData({ ...formData, position: e.target.value })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
              </div>

              <div>
                <label
                  htmlFor="applicationType"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Type de candidature
                </label>
                <select
                  id="applicationType"
                  value={formData.applicationType}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      applicationType: e.target.value,
                    })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                  <option value="response">En réponse à une offre</option>
                  <option value="spontaneous">Spontanée</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="jobType"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Type de poste
                </label>
                <select
                  id="jobType"
                  value={formData.jobType}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      jobType: e.target.value,
                      contractType:
                        e.target.value === "internship" ? "" : formData.contractType,
                    })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                  <option value="job">Emploi</option>
                  <option value="internship">Stage</option>
                </select>
              </div>

              {formData.jobType === "job" && (
                <div>
                  <label
                    htmlFor="contractType"
                    className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                  >
                    Type de contrat
                  </label>
                  <select
                    id="contractType"
                    value={formData.contractType}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        contractType: e.target.value,
                      })
                    }
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  >
                    <option value="cdi">CDI</option>
                    <option value="cdd">CDD</option>
                    <option value="interim">Intérim</option>
                  </select>
                </div>
              )}

              <div>
                <label
                  htmlFor="status"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Statut
                </label>
                <select
                  id="status"
                  value={formData.status}
                  onChange={(e) =>
                    setFormData({ ...formData, status: e.target.value })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                  <option value="applied">Postulée</option>
                  <option value="interview">Entretien</option>
                  <option value="accepted">Acceptée</option>
                  <option value="rejected">Refusée</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="applicationDate"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Date de candidature
                </label>
                <input
                  type="date"
                  id="applicationDate"
                  value={formData.applicationDate}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      applicationDate: e.target.value,
                    })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
              </div>

              <div>
                <label
                  htmlFor="location"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Localisation
                </label>
                <input
                  type="text"
                  id="location"
                  value={formData.location}
                  onChange={(e) =>
                    setFormData({ ...formData, location: e.target.value })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
              </div>

              <div>
                <label
                  htmlFor="salary"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Salaire
                </label>
                <input
                  type="text"
                  id="salary"
                  value={formData.salary}
                  onChange={(e) =>
                    setFormData({ ...formData, salary: e.target.value })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  placeholder="Ex: 45-50k €"
                />
              </div>

              <div>
                <label
                  htmlFor="contactEmail"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Email de contact {formData.contactPhone ? "(Facultatif)" : "*"}
                </label>
                <input
                  type="email"
                  id="contactEmail"
                  value={formData.contactEmail}
                  onChange={(e) =>
                    setFormData({ ...formData, contactEmail: e.target.value })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
              </div>

              <div>
                <label
                  htmlFor="contactPhone"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Téléphone de contact {formData.contactEmail ? "(Facultatif)" : "*"}
                </label>
                <input
                  type="tel"
                  id="contactPhone"
                  value={formData.contactPhone}
                  onChange={(e) =>
                    setFormData({ ...formData, contactPhone: e.target.value })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
              </div>

              <div>
                <label
                  htmlFor="url"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  URL de l'offre (facultatif)
                </label>
                <input
                  type="url"
                  id="url"
                  value={formData.url}
                  onChange={(e) =>
                    setFormData({ ...formData, url: e.target.value })
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
              </div>
            </div>

            {/* Fichiers */}
            <div className="border-t pt-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Documents
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="coverLetter"
                    className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                  >
                    Lettre de motivation (PDF, Word) - Facultatif
                  </label>
                  <div className="mt-2">
                    {formData.coverLetterPath && (
                      <div className="mb-2 p-2 bg-green-50 dark:bg-green-900 rounded flex items-center justify-between">
                        <span className="text-sm text-green-700 dark:text-green-200">
                          ✓ Fichier téléchargé
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            setFormData({
                              ...formData,
                              coverLetterPath: "",
                            })
                          }
                          className="text-red-600 hover:text-red-500 text-sm"
                        >
                          Supprimer
                        </button>
                      </div>
                    )}
                    <input
                      type="file"
                      id="coverLetter"
                      onChange={(e) => handleFileUpload(e, "coverLetter")}
                      accept=".pdf,.doc,.docx"
                      disabled={uploadingCoverLetter}
                      className="block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:file:bg-indigo-900 dark:file:text-indigo-200"
                    />
                    {uploadingCoverLetter && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Téléchargement...
                      </p>
                    )}
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="companyLogo"
                    className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                  >
                    Logo de l'entreprise (PNG, JPG) - Facultatif
                  </label>
                  <div className="mt-2">
                    {formData.companyLogoPath && (
                      <div className="mb-2">
                        <img
                          src={formData.companyLogoPath}
                          alt="Logo"
                          className="h-16 w-16 object-contain mb-2"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            setFormData({
                              ...formData,
                              companyLogoPath: "",
                            })
                          }
                          className="text-red-600 hover:text-red-500 text-sm"
                        >
                          Supprimer
                        </button>
                      </div>
                    )}
                    <input
                      type="file"
                      id="companyLogo"
                      onChange={(e) => handleFileUpload(e, "logo")}
                      accept="image/png,image/jpeg,image/gif,image/webp"
                      disabled={uploadingLogo}
                      className="block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:file:bg-indigo-900 dark:file:text-indigo-200"
                    />
                    {uploadingLogo && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Téléchargement...
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div>
              <label
                htmlFor="notes"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Notes
              </label>
              <textarea
                id="notes"
                rows={3}
                value={formData.notes}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            {/* Rappels */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Rappels
                </label>
                <button
                  type="button"
                  onClick={addReminder}
                  className="text-sm text-indigo-600 hover:text-indigo-500"
                >
                  + Ajouter un rappel
                </button>
              </div>
              <div className="space-y-2">
                {formData.reminders.map((reminder: any, index: number) => (
                  <div key={index} className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Titre du rappel"
                      value={reminder.title}
                      onChange={(e) =>
                        updateReminder(index, "title", e.target.value)
                      }
                      className="flex-1 rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                    <input
                      type="date"
                      value={reminder.date}
                      onChange={(e) =>
                        updateReminder(index, "date", e.target.value)
                      }
                      className="rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                    <button
                      type="button"
                      onClick={() => removeReminder(index)}
                      className="px-3 py-2 text-red-600 hover:text-red-500"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {error && (
              <div className="text-red-600 text-sm text-center">{error}</div>
            )}

            <div className="flex gap-4">
              <Link
                href="/dashboard"
                className="flex-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 text-center"
              >
                Annuler
              </Link>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? "Ajout..." : "Ajouter"}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
