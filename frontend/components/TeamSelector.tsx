"use client";

import { Team } from "@/lib/api";

interface Props {
  teams: Team[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export default function TeamSelector({ teams, selected, onSelect }: Props) {
  return (
    <div className="panel">
      <h2>1 · Elige tu selección</h2>
      <div className="team-grid">
        {teams.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`team-btn ${selected === t.id ? "selected" : ""}`}
            disabled={!t.available}
            title={t.available ? t.name : `${t.name} (plantilla no disponible)`}
            onClick={() => onSelect(t.id)}
          >
            {t.name}
          </button>
        ))}
      </div>
    </div>
  );
}
