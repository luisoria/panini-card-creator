"use client";

import { useEffect, useState } from "react";
import CardPreview from "@/components/CardPreview";
import PhotoUploader from "@/components/PhotoUploader";
import PlayerForm from "@/components/PlayerForm";
import TeamSelector from "@/components/TeamSelector";
import { fetchTeams, generateCard, PlayerData, Team } from "@/lib/api";

const EMPTY: PlayerData = {
  playerName: "",
  birthDate: "",
  height: "",
  weight: "",
  club: "",
};

export default function Home() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [team, setTeam] = useState<string | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [data, setData] = useState<PlayerData>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);

  useEffect(() => {
    fetchTeams()
      .then(setTeams)
      .catch(() => setError("No se pudo conectar con el backend (¿está levantado en :8000?)."));
  }, []);

  const ready =
    team &&
    photo &&
    data.playerName.trim() &&
    /^\d{1,2}-\d{1,2}-\d{4}$/.test(data.birthDate.trim()) &&
    data.height.trim() &&
    data.weight.trim() &&
    data.club.trim();

  const handleGenerate = async () => {
    if (!ready || !team || !photo) return;
    setLoading(true);
    setError(null);
    try {
      const blob = await generateCard(team, photo, data);
      if (resultUrl) URL.revokeObjectURL(resultUrl);
      setResultUrl(URL.createObjectURL(blob));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error inesperado.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="container">
      <header className="header">
        <h1>
          Card <span>Creator</span> 2026
        </h1>
        <p>Tu rostro, tus datos, la camiseta de tu selección.</p>
      </header>

      <div className="grid">
        <div>
          <TeamSelector teams={teams} selected={team} onSelect={setTeam} />
          <div style={{ height: 20 }} />
          <PhotoUploader onSelect={setPhoto} />
          <div style={{ height: 20 }} />
          <PlayerForm data={data} onChange={setData} />
          <button
            className="btn-primary"
            disabled={!ready || loading}
            onClick={handleGenerate}
          >
            {loading ? "Generando…" : "⚽ Generar mi tarjeta"}
          </button>
          {error && <div className="error-box">{error}</div>}
        </div>

        <CardPreview imageUrl={resultUrl} loading={loading} />
      </div>

      <p className="disclaimer">
        Proyecto de uso personal. Las plantillas, logotipos y marcas pertenecen a
        sus respectivos titulares.
      </p>
    </main>
  );
}
