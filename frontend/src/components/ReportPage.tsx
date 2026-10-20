import React, { useState } from "react";
import { useKeycloak } from "@react-keycloak/web";

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

const handleDownload = async () => {
  setError(null);
  setLoading(true);

  try {
    if (!keycloak?.token) {
      keycloak?.login();
      return;
    }

    await keycloak.updateToken(30);

    const apiUrl = process.env.REACT_APP_API_URL || "http://localhost:8000";

    const periodStart = "2026-01-01";
    const periodEnd = "2026-01-31";

    const res = await fetch(
      `${apiUrl}/api/reports/download?period_start=${periodStart}&period_end=${periodEnd}`,
      { headers: { Authorization: `Bearer ${keycloak.token}` } }
    );

    if (res.status === 401) { keycloak.login(); return; }
    if (res.status === 403) { setError("Недостаточно прав для скачивания отчёта"); return; }
    if (res.status === 409) { setError("Данные за указанный период ещё не обработаны"); return; }
    if (!res.ok) { setError(`Ошибка сервера: ${res.status}`); return; }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "report.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e: any) {
    setError(e?.message || "Не удалось скачать отчёт");
  } finally {
    setLoading(false);
  }
};

  if (!initialized) {
    return <div style={{ padding: 40 }}>Инициализация…</div>;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white shadow-md rounded-lg p-8 w-80 text-center">
        <h1 className="text-xl font-bold mb-6">Usage Reports</h1>

        <button
          onClick={handleDownload}
          disabled={loading}
          className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium py-2 px-4 rounded mb-4"
        >
          {loading ? "Скачивание…" : "Download Report"}
        </button>

        {!keycloak?.authenticated && (
          <div className="bg-red-50 text-red-700 py-2 px-3 rounded text-sm">
            Not authenticated
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-700 py-2 px-3 rounded text-sm mt-2">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;