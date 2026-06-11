"use client";

import { PlayerData } from "@/lib/api";

interface Props {
  data: PlayerData;
  onChange: (data: PlayerData) => void;
}

const FIELDS: {
  key: keyof PlayerData;
  label: string;
  placeholder: string;
  pattern?: string;
  title?: string;
}[] = [
  { key: "playerName", label: "Nombre del Jugador", placeholder: "Luis Díaz" },
  {
    key: "birthDate",
    label: "Fecha de Nacimiento (DD-MM-YYYY)",
    placeholder: "13-1-1997",
    pattern: "\\d{1,2}-\\d{1,2}-\\d{4}",
    title: "Formato: DD-MM-YYYY, ej. 13-1-1997",
  },
  { key: "height", label: "Altura", placeholder: "1,80 m" },
  { key: "weight", label: "Peso", placeholder: "70 kg" },
  {
    key: "club",
    label: "Club Actual y País",
    placeholder: "FC BAYERN MÜNCHEN (GER)",
  },
];

export default function PlayerForm({ data, onChange }: Props) {
  return (
    <div className="panel">
      <h2>3 · Datos del jugador</h2>
      {FIELDS.map((f) => (
        <div className="field" key={f.key}>
          <label htmlFor={f.key}>{f.label}</label>
          <input
            id={f.key}
            type="text"
            required
            value={data[f.key]}
            placeholder={f.placeholder}
            pattern={f.pattern}
            title={f.title}
            onChange={(e) => onChange({ ...data, [f.key]: e.target.value })}
          />
        </div>
      ))}
    </div>
  );
}
