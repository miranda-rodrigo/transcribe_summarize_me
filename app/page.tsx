import React, { useState } from 'react';

export default function Home() {
  const [youtubeURL, setYoutubeURL] = useState('');
  const [status, setStatus] = useState('');
  const [summary, setSummary] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('Processando...');
    const response = await fetch('/api/transcribe-background', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ youtubeURL }),
    });
    const data = await response.json();
    if (data.error) {
      setStatus(`Erro: ${data.error}`);
    } else {
      setStatus('Sucesso!');
      setSummary(data.summary);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">
        Transcreva e sumarize qualquer vídeo do YouTube, tamanho ilimitado.
      </h1>
      <form onSubmit={handleSubmit} className="mb-4">
        <input
          type="text"
          placeholder="Insira o URL do YouTube"
          value={youtubeURL}
          onChange={(e) => setYoutubeURL(e.target.value)}
          className="border p-2 mr-2 w-1/2"
        />
        <button type="submit" className="bg-blue-500 text-white p-2">
          Enviar
        </button>
      </form>
      <p>{status}</p>
      <div className="mt-4">
        <pre>{summary}</pre>
      </div>
    </div>
  );
}
