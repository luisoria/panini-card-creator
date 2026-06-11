const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Team {
  id: string;
  name: string;
  available: boolean;
}

export interface PlayerData {
  playerName: string;
  birthDate: string;
  height: string;
  weight: string;
  club: string;
}

export async function fetchTeams(): Promise<Team[]> {
  const res = await fetch(`${API_URL}/api/teams`);
  if (!res.ok) throw new Error("No se pudo cargar la lista de equipos.");
  return res.json();
}

export async function generateCard(
  team: string,
  photo: File,
  data: PlayerData
): Promise<Blob> {
  const form = new FormData();
  form.append("team", team);
  form.append("player_name", data.playerName);
  form.append("birth_date", data.birthDate);
  form.append("height", data.height);
  form.append("weight", data.weight);
  form.append("club", data.club);
  form.append("photo", photo);

  const res = await fetch(`${API_URL}/api/generate-card`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* respuesta no-JSON */
    }
    throw new Error(detail);
  }
  return res.blob();
}
