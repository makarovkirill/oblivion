import React, { useState } from 'react';
import { X, Flame, ShieldAlert, Loader2, CheckCircle2 } from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { api } from '../api';

interface PanicModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PanicModal: React.FC<PanicModalProps> = ({ isOpen, onClose }) => {
  const { t } = useLanguage();
  const [passphrase, setPassphrase] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [shredSummary, setShredSummary] = useState<any[]>([]);

  if (!isOpen) return null;

  const isLengthValid = passphrase.length >= 16;

  const handlePanicWipe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLengthValid) {
      setError(t('passphraseTooShort'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await api.panicWipe(passphrase);
      setCompleted(true);
      setShredSummary(res.result?.shredded_targets || []);
    } catch (err: any) {
      setError(err.message || 'Panic wipe failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md animate-in fade-in">
      <div className="bg-surface border-2 border-red-600/80 rounded-3xl w-full max-w-lg overflow-hidden shadow-[0_0_50px_rgba(239,68,68,0.3)]">
        <div className="p-5 bg-red-950/40 border-b border-red-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-red-600 text-white shadow-lg shadow-red-600/30">
              <Flame className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h3 className="font-extrabold text-red-200 text-base">{t('panicModalTitle')}</h3>
              <p className="text-[11px] text-red-400 font-mono">OBLIVION EMERGENCY DATA PURGE</p>
            </div>
          </div>
          {!completed && (
            <button onClick={onClose} className="p-1 rounded-lg text-gray-400 hover:text-white transition">
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {completed ? (
          <div className="p-6 space-y-4">
            <div className="p-4 rounded-2xl bg-emerald-950/40 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-3 font-semibold">
              <CheckCircle2 className="w-6 h-6 text-emerald-400 flex-shrink-0" />
              <span>Emergency wipe complete. All configured files, database records, and encryption keys were securely erased.</span>
            </div>
            {shredSummary.length > 0 && (
              <div className="max-h-48 overflow-y-auto p-3 rounded-xl bg-card border border-border text-xs font-mono space-y-1">
                {shredSummary.map((s, idx) => (
                  <div key={idx} className="flex justify-between text-gray-300">
                    <span className="truncate max-w-xs">{s.path}</span>
                    <span className="text-emerald-400 font-bold">{s.status}</span>
                  </div>
                ))}
              </div>
            )}
            <button
              onClick={() => window.location.reload()}
              className="w-full py-2.5 rounded-xl text-xs font-bold bg-gray-800 hover:bg-gray-700 text-white transition"
            >
              Reload Application
            </button>
          </div>
        ) : (
          <form onSubmit={handlePanicWipe} className="p-6 space-y-5">
            <div className="p-4 rounded-2xl bg-red-950/30 border border-red-900/60 text-xs text-red-300 flex items-start gap-3 leading-relaxed">
              <ShieldAlert className="w-5 h-5 flex-shrink-0 text-red-400 mt-0.5" />
              <span>{t('panicModalWarning')}</span>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-bold text-gray-200">
                  {t('panicPassphrasePrompt')}
                </label>
                <span className={`text-[11px] font-mono font-medium ${
                  isLengthValid ? 'text-emerald-400' : 'text-amber-400'
                }`}>
                  {passphrase.length} / 16
                </span>
              </div>
              <input
                type="password"
                value={passphrase}
                onChange={(e) => {
                  setPassphrase(e.target.value);
                  setError(null);
                }}
                placeholder={t('passphrasePlaceholder')}
                autoFocus
                className="w-full px-3.5 py-2.5 rounded-xl bg-card border border-border text-gray-100 text-sm font-mono focus:outline-none focus:border-red-500"
              />
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-950/40 border border-red-800 text-red-300 text-xs">
                {error}
              </div>
            )}

            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-gray-300 hover:text-white rounded-xl transition"
              >
                {t('cancelBtn')}
              </button>
              <button
                type="submit"
                disabled={loading || !isLengthValid}
                className="px-5 py-2.5 rounded-xl text-xs font-extrabold text-white bg-red-600 hover:bg-red-500 flex items-center gap-2 shadow-lg shadow-red-600/30 transition active:scale-95 disabled:opacity-50"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>{t('executePanicBtn')}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
