"use client";

interface Props {
  imageUrl: string | null;
  loading: boolean;
}

export default function CardPreview({ imageUrl, loading }: Props) {
  return (
    <div className="panel preview">
      <h2>Tu tarjeta</h2>
      {loading ? (
        <>
          <div className="spinner" />
          <p style={{ color: "var(--muted)" }}>
            Aplicando face swap y renderizando datos…
          </p>
        </>
      ) : imageUrl ? (
        <>
          <img src={imageUrl} alt="Tarjeta generada" />
          <a className="btn-secondary" href={imageUrl} download="mi-tarjeta-2026.png">
            ⬇ Descargar PNG
          </a>
        </>
      ) : (
        <div className="placeholder">
          Elige equipo, sube tu foto y completa los datos.
          <br />
          La tarjeta aparecerá aquí.
        </div>
      )}
    </div>
  );
}
