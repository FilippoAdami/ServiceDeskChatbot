import React, { useState } from "react";
import { X, AlertCircle, FilePlus, Loader2 } from "lucide-react";

interface NewRequestModalProps {
  conversationId: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (title: string, description: string, category: string) => Promise<void>;
}

export const NewRequestModal: React.FC<NewRequestModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("account");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setError("Compila tutti i campi obbligatori");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onSubmit(title.trim(), description.trim(), category);
      setTitle("");
      setDescription("");
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Errore durante la registrazione della richiesta");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-xl">
        <div className="flex items-center justify-between border-b border-border/80 pb-4">
          <div className="flex items-center gap-2 text-foreground font-semibold">
            <FilePlus className="h-5 w-5 text-primary" />
            <h3 id="modal-title" className="text-lg">Registra Problema IT (SupportRequest)</h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Chiudi modale"
            className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label htmlFor="req-title" className="block text-xs font-medium text-foreground">
              Titolo del Problema *
            </label>
            <input
              id="req-title"
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="es. Mancato recapito email esterne"
              className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="req-category" className="block text-xs font-medium text-foreground">
              Categoria Preliminare
            </label>
            <select
              id="req-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            >
              <option value="account">Account & Credenziali (password, login)</option>
              <option value="email">Posta Elettronica (Outlook, recapito)</option>
              <option value="network">Rete & VPN (Wi-Fi, connessione aziendale)</option>
              <option value="software">Software & Applicativi (Office, CRM, ERP)</option>
              <option value="hardware">Hardware & Periferiche (PC, monitor, stampanti)</option>
              <option value="other">Altro</option>
            </select>
          </div>

          <div>
            <label htmlFor="req-desc" className="block text-xs font-medium text-foreground">
              Descrizione Dettagliata *
            </label>
            <textarea
              id="req-desc"
              rows={4}
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descrivi i sintomi riscontrati, eventuali codici di errore e da quando si verifica il problema..."
              className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-lg border border-border px-4 py-2 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary-hover active:scale-95 transition-transform"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Salvataggio...</span>
                </>
              ) : (
                <span>Registra Richiesta</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
