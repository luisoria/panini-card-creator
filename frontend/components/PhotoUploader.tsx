"use client";

import { useRef, useState } from "react";

interface Props {
  onSelect: (file: File) => void;
}

export default function PhotoUploader({ onSelect }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(file));
    onSelect(file);
  };

  return (
    <div className="panel">
      <h2>2 · Sube tu foto</h2>
      <div
        className="dropzone"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFile(e.dataTransfer.files?.[0]);
        }}
      >
        {preview ? (
          <img src={preview} alt="Vista previa de tu foto" />
        ) : (
          <p>
            Arrastra tu foto aquí o haz clic para seleccionar.
            <br />
            <small>Rostro de frente, bien iluminado, sin gafas oscuras.</small>
          </p>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>
    </div>
  );
}
